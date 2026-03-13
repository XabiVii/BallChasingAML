# select_only_corrected_columns.py
# Deja el CSV únicamente con las columnas de tu LISTA CORREGIDA (match + lobby rank + server + team ball + player stats).
# - No rompe si alguna columna no existe: imprime las faltantes.
# - Al final imprime la lista de columnas que se han quedado.
#
# Ejecuta:
#   python select_only_corrected_columns.py

import os
import pandas as pd

# =========================
# CONFIG (edita rutas)
# =========================
CSV_IN = r"replays_2v2_10000_full_clean_interactive.csv"
CSV_OUT = r"replays_subset_corrected_columns.csv"


def read_csv_safely(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)


def build_keep_columns() -> list[str]:
    keep = set()

    # -------------------------
    # Replay / match level
    # -------------------------
    keep.update([
        "match_guid",
        "duration",
        "overtime",
        "overtime_seconds",
        "min_rank.tier",
        "min_rank.division",
        "min_rank.name",
        "max_rank.tier",
        "max_rank.division",
        "max_rank.name",
        "server.name",
        "server.region",
    ])

    # -------------------------
    # Team-level (ONLY ball module you requested)
    # -------------------------
    teams = ["blue", "orange"]
    TEAM_BALL = ["possession_time", "time_in_side"]
    for t in teams:
        for f in TEAM_BALL:
            keep.add(f"{t}.stats.ball.{f}")

    # -------------------------
    # Player-level (4 jugadores: blue 0/1, orange 0/1)
    # -------------------------
    PLAYER_CORE = ["shots", "shots_against", "goals", "goals_against", "saves", "assists", "score", "shooting_percentage"]

    # Corrected boost list: (NO time_*; NO count_*; only the ones you listed)
    PLAYER_BOOST = [
        "bpm", "bcpm", "avg_amount",
        "amount_collected", "amount_stolen",
        "amount_collected_big", "amount_stolen_big",
        "amount_collected_small", "amount_stolen_small",
        "amount_overfill", "amount_overfill_stolen",
        "amount_used_while_supersonic",
        "percent_zero_boost", "percent_full_boost",
        "percent_boost_0_25", "percent_boost_25_50", "percent_boost_50_75", "percent_boost_75_100",
    ]

    PLAYER_MOVEMENT = [
        "avg_speed", "total_distance",
        "time_supersonic_speed", "time_boost_speed", "time_slow_speed",
        "time_ground", "time_low_air", "time_high_air",
        "time_powerslide", "count_powerslide",
        "avg_powerslide_duration",
        "avg_speed_percentage",
        "percent_slow_speed", "percent_boost_speed", "percent_supersonic_speed",
        "percent_ground", "percent_low_air", "percent_high_air",
    ]

    # Corrected positioning list: only the distances + last defender + percentages you listed
    PLAYER_POSITIONING = [
        "avg_distance_to_ball",
        "avg_distance_to_ball_possession",
        "avg_distance_to_ball_no_possession",
        "avg_distance_to_mates",
        "goals_against_while_last_defender",
        "percent_defensive_third",
        "percent_offensive_third",
        "percent_neutral_third",
        "percent_defensive_half",
        "percent_offensive_half",
        "percent_behind_ball",
        "percent_infront_ball",
        "percent_most_back",
        "percent_most_forward",
        "percent_closest_to_ball",
        "percent_farthest_from_ball",
    ]

    PLAYER_DEMO = ["inflicted", "taken"]

    for t in teams:
        for i in [0, 1]:
            p = f"{t}.players.{i}"
            # Basic identity & participation (only what you requested)
            keep.add(f"{p}.name")
            keep.add(f"{p}.id.platform")
            keep.add(f"{p}.steering_sensitivity")

            # Player stats modules
            for f in PLAYER_CORE:
                keep.add(f"{p}.stats.core.{f}")
            for f in PLAYER_BOOST:
                keep.add(f"{p}.stats.boost.{f}")
            for f in PLAYER_MOVEMENT:
                keep.add(f"{p}.stats.movement.{f}")
            for f in PLAYER_POSITIONING:
                keep.add(f"{p}.stats.positioning.{f}")
            for f in PLAYER_DEMO:
                keep.add(f"{p}.stats.demo.{f}")

    return sorted(keep)


def main():
    if not os.path.exists(CSV_IN):
        raise FileNotFoundError(f"No existe el archivo: {CSV_IN}")

    df = read_csv_safely(CSV_IN)
    keep_cols = build_keep_columns()

    existing = [c for c in keep_cols if c in df.columns]
    missing = [c for c in keep_cols if c not in df.columns]

    print("========================================")
    print("Selección de columnas (LISTA CORREGIDA)")
    print(f"CSV_IN:  {CSV_IN}")
    print(f"Filas:   {len(df):,}")
    print(f"Cols IN: {df.shape[1]:,}")
    print(f"Cols solicitadas: {len(keep_cols):,}")
    print(f"Cols encontradas: {len(existing):,}")
    print(f"Cols faltantes:   {len(missing):,}")
    print("========================================")

    if missing:
        print("\n--- Columnas solicitadas que NO existen en tu CSV ---")
        for c in missing:
            print(f"- {c}")

    df_out = df[existing].copy()
    df_out.to_csv(CSV_OUT, index=False)

    print("\n✅ Guardado:")
    print(f"CSV_OUT: {CSV_OUT}")
    print(f"Cols OUT: {df_out.shape[1]:,}")

    print("\n--- Columnas finales en el CSV_OUT ---")
    for c in df_out.columns:
        print(c)


if __name__ == "__main__":
    main()