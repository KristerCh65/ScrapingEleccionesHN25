import os
import json
from dataclasses import dataclass, asdict
from typing import List, Dict

import requests
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import cv2
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

API_BASE = "https://resultadosgenerales2025-api.cne.hn/esc/v1/actas-documentos"
NIVEL = "01"  # PRESIDENTE

PARTIDOS = [
    "DC",
    "LIBRE",
    "PINU",
    "PLH",
    "PNH",
    "BLANCO",
    "NULOS",
    "TOTAL"
]

CARPETA_PDFS = "actas_pdf"
ARCHIVO_JSON = "resultados_presidente.json"
ARCHIVO_CSV = "resultados_presidente.csv"

DEBUG_IMAGENES = False
CARPETA_DEBUG = "debug"


# ============================================================
# MODELOS
# ============================================================

@dataclass
class MesaInfo:
    publicada: int
    numero: int
    escrutado: bool
    digitalizado: int
    id_informacion_mesa_corporacion: str
    nombre_archivo: str
    etiquetas: List[str]


@dataclass
class ResultadoMesa:
    departamento: str
    municipio: str
    zona: str
    centro: str
    mesa_numero: int
    id_mesa: str
    pdf_url: str
    etiquetas: List[str]
    votos: Dict[str, int]
    ocr_status: str  # OK | SIN PDF | ERROR OCR


# ============================================================
# API
# ============================================================

def get_json(url: str):
    print(f"GET {url}")
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def obtener_municipios(dep: str):
    return get_json(f"{API_BASE}/{NIVEL}/{dep}/municipios")


def obtener_zonas(dep: str, mun: str):
    return get_json(f"{API_BASE}/{NIVEL}/{dep}/{mun}/zonas")


def obtener_centros(dep: str, mun: str, zona: str):
    return get_json(f"{API_BASE}/{NIVEL}/{dep}/{mun}/{zona}/puestos")


def obtener_mesas(dep: str, mun: str, zona: str, centro: str):
    data = get_json(f"{API_BASE}/{NIVEL}/{dep}/{mun}/{zona}/{centro}/mesas")

    mesas = []
    for m in data:
        mesas.append(MesaInfo(
            publicada=m.get("publicada"),
            numero=m.get("numero"),
            escrutado=m.get("escrutado"),
            digitalizado=m.get("digitalizado"),
            id_informacion_mesa_corporacion=m.get("id_informacion_mesa_corporacion"),
            nombre_archivo=m.get("nombre_archivo"),
            etiquetas=m.get("etiquetas", [])
        ))
    return mesas


def filtrar_mesas_validas(mesas: List[MesaInfo]):
    """
    Procesar TODAS las mesas, incluso sin PDF.
    """
    return mesas


# ============================================================
# PDF Y PROCESAMIENTO OCR
# ============================================================

def descargar_pdf(url: str, nombre: str) -> str:
    os.makedirs(CARPETA_PDFS, exist_ok=True)
    ruta = os.path.join(CARPETA_PDFS, nombre)

    if os.path.exists(ruta):
        return ruta

    print(f"Descargando PDF: {url}")
    r = requests.get(url)
    r.raise_for_status()

    with open(ruta, "wb") as f:
        f.write(r.content)

    return ruta


def pdf_a_imagen(ruta_pdf: str) -> Image.Image:
    """
    Convierte PDF a imagen usando poppler (disponible en Linux/Codespaces).
    """
    with open(ruta_pdf, "rb") as f:
        data = f.read()
    pages = convert_from_bytes(data, dpi=300)
    return pages[0]


def preprocess_image(img: Image.Image):
    cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)
    th = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35, 11
    )
    return Image.fromarray(th)


def recorte_tabla(img: Image.Image):
    w, h = img.size
    left = int(w * 0.10)
    right = int(w * 0.63)
    top = int(h * 0.43)
    bottom = int(h * 0.78)
    tabla = img.crop((left, top, right, bottom))

    if DEBUG_IMAGENES:
        os.makedirs(CARPETA_DEBUG, exist_ok=True)
        tabla.save(os.path.join(CARPETA_DEBUG, "tabla.png"))

    return tabla


def dividir_filas(tabla: Image.Image):
    w, h = tabla.size
    fila_h = h // 8
    return [tabla.crop((0, fila_h*i, w, fila_h*(i+1))) for i in range(8)]


def ocr_num(img: Image.Image):
    config = "--psm 7 -c tessedit_char_whitelist=0123456789"
    txt = pytesseract.image_to_string(img, config=config)
    txt = "".join(c for c in txt if c.isdigit())
    return int(txt) if txt else 0


def leer_votos_presidente(img: Image.Image):
    tabla = recorte_tabla(img)
    tabla = preprocess_image(tabla)
    filas = dividir_filas(tabla)
    numeros = [ocr_num(f) for f in filas]
    return dict(zip(PARTIDOS, numeros))


# ============================================================
# PROCESAR UNA MESA
# ============================================================

def procesar_mesa(args):
    mesa, dep, mun, zona, centro = args

    try:
        # Sin PDF → registrar
        if not mesa.nombre_archivo or ".pdf" not in mesa.nombre_archivo.lower():
            return ResultadoMesa(
                departamento=dep,
                municipio=mun,
                zona=zona,
                centro=centro,
                mesa_numero=mesa.numero,
                id_mesa=mesa.id_informacion_mesa_corporacion,
                pdf_url=None,
                etiquetas=mesa.etiquetas,
                votos={p: None for p in PARTIDOS},
                ocr_status="SIN PDF"
            )

        nombre_local = f"mesa_{mesa.numero}_{mesa.id_informacion_mesa_corporacion}.pdf"
        ruta = descargar_pdf(mesa.nombre_archivo, nombre_local)

        img = pdf_a_imagen(ruta)
        votos = leer_votos_presidente(img)

        return ResultadoMesa(
            departamento=dep,
            municipio=mun,
            zona=zona,
            centro=centro,
            mesa_numero=mesa.numero,
            id_mesa=mesa.id_informacion_mesa_corporacion,
            pdf_url=mesa.nombre_archivo,
            etiquetas=mesa.etiquetas,
            votos=votos,
            ocr_status="OK"
        )

    except Exception as e:
        print(f"ERROR OCR Mesa {mesa.numero}: {e}")
        return ResultadoMesa(
            departamento=dep,
            municipio=mun,
            zona=zona,
            centro=centro,
            mesa_numero=mesa.numero,
            id_mesa=mesa.id_informacion_mesa_corporacion,
            pdf_url=mesa.nombre_archivo,
            etiquetas=mesa.etiquetas,
            votos={p: None for p in PARTIDOS},
            ocr_status="ERROR OCR"
        )


# ============================================================
# GUARDAR RESULTADOS
# ============================================================

def guardar(resultados: List[ResultadoMesa]):
    data = [asdict(r) for r in resultados]

    with open(ARCHIVO_JSON, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    filas = []
    for r in resultados:
        base = {
            "departamento": r.departamento,
            "municipio": r.municipio,
            "zona": r.zona,
            "centro": r.centro,
            "mesa": r.mesa_numero,
            "id_mesa": r.id_mesa,
            "pdf": r.pdf_url,
            "estado_ocr": r.ocr_status,
            "etiquetas": "|".join(r.etiquetas),
        }
        if r.votos:
            base.update(r.votos)
        filas.append(base)

    df = pd.DataFrame(filas)
    df.to_csv(ARCHIVO_CSV, index=False, encoding="utf-8-sig")

    print("\nRESULTADOS GUARDADOS:")
    print(" →", ARCHIVO_JSON)
    print(" →", ARCHIVO_CSV)


# ============================================================
# RECORRIDO GENERAL
# ============================================================

def procesar_departamento(dep: str, dep_nombre: str):
    tareas = []

    municipios = obtener_municipios(dep)
    for m in municipios:
        mun_id = m["id"]
        mun_desc = m["descripcion"]

        zonas = obtener_zonas(dep, mun_id)
        for z in zonas:
            zona_id = z["id"]
            zona_desc = z["descripcion"]

            centros = obtener_centros(dep, mun_id, zona_id)
            for c in centros:
                centro_id = c["id"]
                centro_desc = c["descripcion"]

                mesas = obtener_mesas(dep, mun_id, zona_id, centro_id)
                mesas_ok = filtrar_mesas_validas(mesas)

                for mesa in mesas_ok:
                    tareas.append((mesa, dep_nombre, mun_desc, zona_desc, centro_desc))

    print(f"\nMesas a procesar: {len(tareas)}")

    resultados = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(procesar_mesa, t) for t in tareas]

        for i, f in enumerate(as_completed(futures), 1):
            try:
                res = f.result()
                resultados.append(res)
                print(f"[{i}/{len(futures)}] Mesa {res.mesa_numero} → {res.ocr_status}")
            except Exception as e:
                print("ERROR en tarea:", e)

    guardar(resultados)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Cambia "04" y "COPÁN" si querés otro departamento
    procesar_departamento("04", "COPÁN")
