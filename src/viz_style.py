"""Estilo y paleta de los gráficos.

La paleta no es decorativa: el orden de los colores está elegido para que
cualquier par de series *adyacentes* en un apilado siga siendo distinguible
con daltonismo (protanopía, deuteranopía, tritanopía). Se validó con el
criterio ΔE en OKLab: ≥8 bajo simulación de daltonismo y ≥15 con visión
normal, para todos los pares contiguos, sobre fondo claro y oscuro.

Amarillo y aqua quedan bajo 3:1 de contraste contra el fondo claro, así que
los gráficos que los usan llevan **etiquetas directas**, no solo leyenda.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory

# --- Superficies e ink -------------------------------------------------------
SUPERFICIE = "#fcfcfb"
INK = "#0b0b0b"
INK_SEC = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
EJE = "#c3c2b7"

# --- Paleta por grupo tecnológico -------------------------------------------
# Orden = orden de apilado: fósiles abajo, renovables arriba.
COLORES: dict[str, str] = {
    "Carbón": "#e34948",                   # rojo
    "Gas natural": "#4a3aa7",              # violeta
    "Diésel y otros térmicos": "#eb6834",  # naranjo
    "Hidráulica": "#2a78d6",               # azul
    "Eólica": "#1baf7a",                   # aqua
    "Solar": "#eda100",                    # amarillo
    "Biomasa y geotermia": "#008300",      # verde
}

# Para gráficos de énfasis: una serie destacada, el resto en gris.
GRIS_CONTEXTO = "#c9c8c2"


def aplicar_estilo() -> None:
    """Configura matplotlib. Llamar una vez al inicio del notebook."""
    mpl.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "savefig.bbox": "tight",
        "savefig.dpi": 150,
        "figure.dpi": 110,

        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Helvetica", "Arial"],
        "font.size": 10,

        "axes.edgecolor": EJE,
        "axes.labelcolor": INK_SEC,
        "axes.titlecolor": INK,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        # Espacio para que el subtítulo quepa entre el título y el eje.
        "axes.titlepad": 32,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,

        "grid.color": GRID,
        "grid.linewidth": 0.8,

        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.direction": "out",
        "ytick.direction": "out",

        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": INK_SEC,

        "lines.linewidth": 2.0,
        "lines.markersize": 8,
    })


def encabezado(ax, titulo: str, subtitulo: str) -> None:
    """Título + subtítulo explicativo, alineados a la izquierda y sin chocar."""
    ax.set_title(titulo)
    ax.text(0.0, 1.015, subtitulo, transform=ax.transAxes,
            fontsize=9.5, color=INK_SEC, va="bottom", ha="left")


def etiqueta_derecha(ax, y, texto: str, color: str, dx: float = 0.015, **kw) -> None:
    """Etiqueta directa al costado derecho, FUERA del área de datos.

    Usa un transform mixto (x en fracción de ejes, y en unidades de datos) para
    que la etiqueta quede afuera sin tener que estirar el xlim — así la grilla
    no se extiende hacia la zona de texto.
    """
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    kw.setdefault("fontsize", 9.5)
    kw.setdefault("fontweight", "medium")
    ax.text(1 + dx, y, texto, transform=tr, color=color,
            va="center", ha="left", clip_on=False, **kw)


def espacio_etiquetas(fig, derecha: float = 0.76) -> None:
    """Reserva margen derecho para las etiquetas directas."""
    fig.subplots_adjust(right=derecha)


def fuente(fig, y: float = -0.02,
           texto: str = "Fuente: Comisión Nacional de Energía (CNE) · datos.gob.cl") -> None:
    """Pie de fuente, abajo a la izquierda. Bajar `y` si hay leyenda debajo."""
    fig.text(0.0, y, texto, fontsize=8, color=INK_MUTED, ha="left", va="top")
