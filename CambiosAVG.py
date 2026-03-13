# convert_time_seconds_to_percent.py
# Convierte columnas de tiempo (segundos) a porcentaje usando la duración del partido.
# Crea nuevas columnas con sufijo "_pct" (0–100).
#
# Ejecuta:
#   python convert_time_seconds_to_percent.py

import os
import pandas as pd

# =========================
# CONFIG
# =========================
CSV_IN = r"replays_subset_corrected_columns.csv"   # tu CSV actual
CSV_OUT = r"replays_subset_with_time_percentages.csv"

DURATION_COL = "duration"  # segundos del partido (match-level)

# Tiempo a convertir (team ball)
TEAM_TIME_COLS = [
    "blue.stats.ball.possession_time",
    "blue.stats.ball.time_in_side",
    "orange.stats.ball.possession_time",
    "orange.stats.ball.time_in_side",
]

# Tiempos a convertir (player movement) -> para los 4 jugadores
PLAYER_TIME_SUFFIXES = [
    "time_supersonic_speed",
    "time_boost_speed",
    "time_slow_speed",
    "time_ground",
    "time_low_air",
    "time_high_air",
    "time_powerslide",
]

# =========================
# HELPERS
# =========================
def read_csv_safely(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)

def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")

def add_pct_column(df: pd.DataFrame, time_col: str, duration_col: str) -> None:
    """
    Añade columna time_col + "_pct" como (time / duration)*100.
    Si duration <= 0 o NaN => resultado NaN.
    """
    if time_col not in df.columns:
        print(f"[WARN] No existe: {time_col}")
        return
    if duration_col not in df.columns:
        raise KeyError(f"No existe la columna de duración: {duration_col}")

    t = to_numeric(df[time_col])
    d = to_numeric(df[duration_col])

    pct = (t / d) * 100.0
    pct = pct.where(d > 0)  # evita dividir entre 0 o negativos

    df[f"{time_col}_pct"] = pct

def main():
    if not os.path.exists(CSV_IN):
        raise FileNotFoundError(f"No existe el archivo: {CSV_IN}")

    df = read_csv_safely(CSV_IN)

    # 1) Team ball time -> %
    for col in TEAM_TIME_COLS:
        add_pct_column(df, col, DURATION_COL)

    # 2) Player movement time -> % (para cada jugador)
    for team in ["blue", "orange"]:
        for i in [0, 1]:
            base = f"{team}.players.{i}.stats.movement"
            for suf in PLAYER_TIME_SUFFIXES:
                col = f"{base}.{suf}"
                add_pct_column(df, col, DURATION_COL)

    df.to_csv(CSV_OUT, index=False)

    print("✅ Hecho")
    print(f"Entrada: {CSV_IN}")
    print(f"Salida:  {CSV_OUT}")
    print("Nuevas columnas añadidas: sufijo '_pct' (0–100)")

if __name__ == "__main__":
    main()