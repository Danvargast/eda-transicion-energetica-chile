"""Limpieza de la generación bruta mensual del SEN.

El CSV crudo de la CNE trae cuatro problemas reales que hay que resolver antes
de analizar. Cada función documenta el criterio usado, porque varias de estas
decisiones cambian los resultados:

1. Formato chileno: BOM UTF-8 y coma decimal ("11843,1" = 11 843,1 MWh).
2. Ruido de punto flotante: valores como 11843.1000000001.
3. Filas repetidas desde 2022-03: la CNE empezó a desagregar por *unidad*
   generadora manteniendo el mismo `codigo_central`. Hay que SUMARLAS, no
   eliminarlas (ver `agregar_unidades`).
4. Un valor negativo aislado (-3,16 MWh en 2016-03).

Uso:
    python src/clean.py     # escribe data/processed/generacion_sen.parquet
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "generacion-bruta-mensual-sen.csv"
PROCESSED = ROOT / "data" / "processed" / "generacion_sen.parquet"

# Las 13 tecnologías del CSV colapsadas en 7 grupos legibles.
# El orden del diccionario es el orden de apilado en los gráficos:
# fósiles abajo, renovables arriba.
GRUPOS: dict[str, str] = {
    "Carbón": "Carbón",
    "Gas Natural": "Gas natural",
    "Petróleo Diesel": "Diésel y otros térmicos",
    "Térmica": "Diésel y otros térmicos",
    "Cogeneración": "Diésel y otros térmicos",
    "Hidráulica de Embalse": "Hidráulica",
    "Hidráulica de Pasada": "Hidráulica",
    "Mini Hidráulica de Pasada": "Hidráulica",
    "Eólica": "Eólica",
    "Solar Fotovoltaica": "Solar",
    "Concentración Solar de Potencia": "Solar",
    "Biomasa": "Biomasa y geotermia",
    "Geotermica": "Biomasa y geotermia",
}

ORDEN_GRUPOS = [
    "Carbón",
    "Gas natural",
    "Diésel y otros térmicos",
    "Hidráulica",
    "Eólica",
    "Solar",
    "Biomasa y geotermia",
]

FOSILES = {"Carbón", "Gas natural", "Diésel y otros térmicos"}

CLAVE_UNIDAD = ["anio", "mes", "codigo_central", "tecnologia", "subsistema", "clasificacion"]


def cargar_crudo(path: Path = RAW) -> pd.DataFrame:
    """Lee el CSV respetando el BOM y la coma decimal chilena."""
    return pd.read_csv(path, encoding="utf-8-sig", decimal=",")


def agregar_unidades(df: pd.DataFrame) -> pd.DataFrame:
    """Suma las filas que comparten central+mes+tecnología.

    Desde 2022-03 la CNE reporta unidades generadoras por separado bajo el
    mismo `codigo_central`. Si en vez de sumar se eliminaran los duplicados,
    la serie perdería ~1,1% de la generación y aparecería un escalón falso
    justo en marzo de 2022. Se conserva `tecnologia` en la clave para no
    fusionar centrales duales (una misma central que opera con diésel y con
    gas reporta ambas, y son cosas distintas).
    """
    return df.groupby(CLAVE_UNIDAD, as_index=False, observed=True)["generacion_mwh"].sum()


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica toda la limpieza y devuelve el dataset analítico."""
    df = df.copy()

    # 2. El ruido de punto flotante no aporta: 0,1 MWh es la resolución útil.
    df["generacion_mwh"] = df["generacion_mwh"].round(1)

    # 4. Un único negativo (-3,16 MWh), consumo propio de una minihidro.
    #    Es 3e-9 del total: se lleva a 0 y se deja constancia.
    df["generacion_mwh"] = df["generacion_mwh"].clip(lower=0)

    # 3. Unidades de una misma central.
    df = agregar_unidades(df)

    # Fecha al primer día del mes: permite resample y ordena bien.
    df["fecha"] = pd.to_datetime(dict(year=df.anio, month=df.mes, day=1))

    # Grupos tecnológicos.
    df["grupo"] = df["tecnologia"].map(GRUPOS)
    if df["grupo"].isna().any():
        faltan = sorted(df.loc[df.grupo.isna(), "tecnologia"].unique())
        raise ValueError(f"Tecnologías sin grupo asignado: {faltan}")
    df["grupo"] = pd.Categorical(df["grupo"], categories=ORDEN_GRUPOS, ordered=True)

    df["es_fosil"] = df["grupo"].astype(str).isin(FOSILES)

    # `subsistema` es un atributo fijo de cada central (ninguna cambia de
    # sistema en toda la serie), así que sirve como proxy geográfico estable:
    # SING = Norte Grande, SIC = centro-sur. Ojo: la etiqueta es histórica,
    # ambos sistemas se interconectaron en el SEN en noviembre de 2017.
    df["zona"] = df["subsistema"].map({"SING": "Norte Grande", "SIC": "Centro-sur"})

    # Marca los años con los 12 meses, para no comparar un año parcial.
    meses = df.groupby("anio")["mes"].transform("nunique")
    df["anio_completo"] = meses == 12

    cols = [
        "fecha", "anio", "mes", "anio_completo", "grupo", "tecnologia",
        "clasificacion", "es_fosil", "subsistema", "zona",
        "codigo_central", "generacion_mwh",
    ]
    return df[cols].sort_values(["fecha", "grupo", "codigo_central"]).reset_index(drop=True)


def matriz_anual(df: pd.DataFrame, solo_completos: bool = True) -> pd.DataFrame:
    """TWh por año y grupo tecnológico (filas=año, columnas=grupo)."""
    if solo_completos:
        df = df[df.anio_completo]
    m = df.pivot_table(
        index="anio", columns="grupo", values="generacion_mwh",
        aggfunc="sum", fill_value=0.0, observed=True,
    )
    return (m / 1e6).reindex(columns=ORDEN_GRUPOS, fill_value=0.0)


def share_anual(df: pd.DataFrame, solo_completos: bool = True) -> pd.DataFrame:
    """Participación % por año y grupo tecnológico."""
    m = matriz_anual(df, solo_completos)
    return m.div(m.sum(axis=1), axis=0) * 100


def main() -> None:
    crudo = cargar_crudo()
    print(f"Crudo:   {crudo.shape[0]:,} filas".replace(",", "."))
    df = limpiar(crudo)
    print(f"Limpio:  {df.shape[0]:,} filas".replace(",", "."))
    print(f"Periodo: {df.fecha.min():%Y-%m} a {df.fecha.max():%Y-%m}")
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED, index=False)
    print(f"Guardado: {PROCESSED}")


if __name__ == "__main__":
    main()
