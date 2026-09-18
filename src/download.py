"""Descarga la generación bruta mensual del Sistema Eléctrico Nacional (SEN).

Fuente: Comisión Nacional de Energía (CNE), vía el Portal de Datos Abiertos
de Chile (datos.gob.cl). Licencia abierta, sin API key.

Uso:
    python src/download.py            # descarga si no existe
    python src/download.py --force    # vuelve a descargar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DEST = RAW_DIR / "generacion-bruta-mensual-sen.csv"

URL = (
    "https://datos.gob.cl/dataset/0e54541d-e5b4-47a5-9cc8-0bd5062d1c88"
    "/resource/389a1943-9c3d-4957-982a-58e3fb0c1bdb"
    "/download/generacion-bruta-mensual-sen.csv"
)

# El portal rechaza clientes sin User-Agent de navegador.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def download(dest: Path = DEST, force: bool = False) -> Path:
    if dest.exists() and not force:
        mb = dest.stat().st_size / 1e6
        print(f"Ya existe: {dest} ({mb:.1f} MB). Usa --force para redescargar.")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando desde datos.gob.cl ...")

    with requests.get(URL, headers=HEADERS, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        tmp.replace(dest)

    mb = dest.stat().st_size / 1e6
    print(f"Listo: {dest} ({mb:.1f} MB)")
    return dest


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--force", action="store_true", help="redescargar aunque exista")
    args = p.parse_args()
    try:
        download(force=args.force)
    except requests.HTTPError as e:
        print(f"Error HTTP: {e}", file=sys.stderr)
        print(
            "Si el enlace cambió, búscalo en: "
            "https://datos.gob.cl/dataset/generacion-bruta",
            file=sys.stderr,
        )
        sys.exit(1)
