# ScrapingEleccionesHN25

Scraper + OCR para extraer resultados **presidenciales** desde las actas del CNE Honduras 2025.

## 🚀 Qué hace

- Recorre automáticamente:
  - Departamento → Municipio → Zona → Centro de votación → Mesas
- Consulta la API pública del CNE 2025
- Descarga los PDFs de las actas (cuando existen)
- Extrae la tabla de resultados presidenciales con OCR:
  - DC
  - LIBRE
  - PINU
  - PLH
  - PNH
  - BLANCO
  - NULOS
  - TOTAL
- Guarda todo en:
  - `resultados_presidente.json`
  - `resultados_presidente.csv`
- Registra estado de OCR por mesa:
  - `OK`
  - `SIN PDF`
  - `ERROR OCR`

## 🐳 Uso en GitHub Codespaces

El repo incluye un entorno de desarrollo listo en `.devcontainer/`.

1. Abrir el repo en Codespaces.
2. Esperar a que termine la configuración automática (instala Tesseract, Poppler y dependencias Python).
3. Ejecutar:

```bash
python cne_scraper.py
```

Los resultados se generan en:
- `actas_pdf/`
- `resultados_presidente.json`
- `resultados_presidente.csv`

## 🤖 Automatización con GitHub Actions

El workflow en `.github/workflows/update-data.yml`:

- Puede ejecutarse manualmente (workflow_dispatch)
- Puede ejecutarse de forma periódica (cron)
- Corre el scraper
- Actualiza CSV/JSON
- Hace commit automático al repositorio si hay cambios

## ⚠️ Notas

- Este proyecto es solo para fines de análisis y transparencia.
- Respeta siempre los términos de uso de los datos públicos del CNE.
