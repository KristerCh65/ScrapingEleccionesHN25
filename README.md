# 🇭🇳 CNE Scraper – Elecciones Honduras 2025  
Scraper + OCR para extraer los resultados presidenciales desde las actas del CNE Honduras 2025.

## 🚀 Funcionalidades
- Recorre automáticamente:
  - Departamento → Municipio → Zona → Centro → Mesas
- Descarga PDFs de cada mesa
- Extrae la tabla de resultados presidenciales con OCR
- Guarda resultados en:
  - `resultados_presidente.json`
  - `resultados_presidente.csv`
- Maneja estos estados:
  - Divulgada Correctamente
  - Pendiente de Revisión
  - Pendiente de Transmisión
  - Pendiente de Recibir
  - Publicada con Inconsistencias
  - Sin PDF

## 🐳 GitHub Codespaces (recomendado)
El repo incluye `.devcontainer/` que instala automáticamente:

- Python 3.10
- tesseract-ocr
- poppler-utils
- pdf2image, pytesseract, pandas, numpy, opencv, etc.

### Para correr el scraper:
- python cne_scraper.py

## 📁 Resultados
Se almacenan en:
- `/actas_pdf/`
- `resultados_presidente.json`
- `resultados_presidente.csv`

## 🤝 Contribuciones
Todo aporte es bienvenido.
