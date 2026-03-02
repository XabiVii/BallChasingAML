# clean_cols_interactive_with_imputation.py
# - Lee el CSV
# - ELIMINA automáticamente todo lo relacionado con cámara (columnas) y muestra cuáles elimina
# - ELIMINA automáticamente partidas con duración < 15s y muestra cuántas filas elimina
# - MUESTRA al principio la lista de columnas candidatas (muchos nulos)
# - Para cada candidata, pregunta:
#     1) ¿Eliminar columna?
#     2) Si NO se elimina: ¿Con qué valor/relleno completar los nulls? (incluye opción boolean True/False)
# - Guarda una copia con los cambios.
#
# Ejecuta:
#   python clean_cols_interactive_with_imputation.py

import os
import sys
import pandas as pd
import numpy as np

# =========================
# CONFIG (edita esto una vez)
# =========================
CSV_IN = r"replays_2v2_10000_full.csv"
CSV_OUT = r"replays_2v2_10000_full_clean_interactive.csv"

THRESHOLD_NULL_RATIO = 0.0001        # columnas candidatas si null_ratio > este umbral
TREAT_EMPTY_STRINGS_AS_NULL = True   # "" o "   " -> NA
KEEP_COLS = []                       # columnas que nunca se proponen para borrar

SHOW_EXAMPLES = 5                    # cuántos ejemplos mostrar de valores no nulos

# Si hay muchísimas candidatas y no quieres imprimir todas:
MAX_PRINT_CANDIDATES = 400  # 0 = imprimir todas

# Limpieza automática previa
DROP_CAMERA_COLUMNS = True
DROP_MATCHES_SHORTER_THAN_SECONDS = 3

# Posibles nombres de columna de duración (dependen de cómo aplanaste el JSON)
DURATION_CANDIDATES = [
    "duration",
    "duration_seconds",
    "game.duration",
    "game.duration_seconds",
    "replay.duration",
    "replay.duration_seconds",
    "match.duration",
    "match.duration_seconds",
]

# =========================
# HELPERS
# =========================
def read_csv_safely(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)

def is_numeric_dtype(dtype) -> bool:
    return pd.api.types.is_numeric_dtype(dtype)

def is_bool_dtype(dtype) -> bool:
    return pd.api.types.is_bool_dtype(dtype)

def shorten(x, n=180):
    s = str(x)
    return s if len(s) <= n else s[:n] + "..."

def print_examples(series: pd.Series, n=5):
    non_null = series.dropna()
    if non_null.empty:
        print("  (no hay valores no nulos para mostrar)")
        return
    for i, v in enumerate(non_null.head(n).tolist(), start=1):
        print(f"  {i}. {shorten(v)}")

def ask_action(col: str, null_pct: float, dtype: str) -> str:
    """
    d = drop
    k = keep + impute
    s = show examples (luego vuelve a preguntar)
    q = quit (sin guardar)
    """
    while True:
        print("\n----------------------------------------")
        print(f"Columna candidata: {col}")
        print(f"  - null_pct: {null_pct:.2f}%")
        print(f"  - dtype: {dtype}")
        ans = input("Acción: [d]=eliminar, [k]=mantener y rellenar nulls, [s]=ver ejemplos, [q]=salir: ").strip().lower()
        if ans in {"d", "k", "s", "q"}:
            return ans
        print("Entrada no válida. Usa d/k/s/q.")

def ask_imputation_numeric(col: str, series: pd.Series) -> tuple[str, object]:
    while True:
        print("\nRelleno de nulls (columna numérica):")
        print("  [1] media")
        print("  [2] mediana")
        print("  [3] moda (valor más frecuente)")
        print("  [4] constante (lo indicas tú)")
        print("  [5] cero")
        print("  [6] no rellenar (dejar nulls)")
        choice = input("Elige 1/2/3/4/5/6: ").strip()

        s = series.dropna()
        if choice == "1":
            if s.empty:
                print("No hay datos no nulos para calcular media. Elige constante.")
                continue
            return ("mean", float(s.mean()))
        if choice == "2":
            if s.empty:
                print("No hay datos no nulos para calcular mediana. Elige constante.")
                continue
            return ("median", float(s.median()))
        if choice == "3":
            if s.empty:
                print("No hay datos no nulos para calcular moda. Elige constante.")
                continue
            mode = s.mode(dropna=True)
            if mode.empty:
                print("No se pudo calcular moda. Elige constante.")
                continue
            try:
                return ("mode", float(mode.iloc[0]))
            except Exception:
                return ("mode", mode.iloc[0])
        if choice == "4":
            raw = input(f"Valor constante para '{col}' (ej: 0, -1, 3.14): ").strip()
            try:
                val = float(raw)
            except ValueError:
                print("Ese valor no parece numérico. Intenta de nuevo.")
                continue
            return ("constant", val)
        if choice == "5":
            return ("zero", 0.0)
        if choice == "6":
            return ("none", None)
        print("Opción no válida.")

def ask_imputation_bool(col: str, series: pd.Series) -> tuple[str, object]:
    while True:
        print("\nRelleno de nulls (columna booleana):")
        print("  [1] True")
        print("  [2] False")
        print("  [3] moda (valor más frecuente)")
        print("  [4] no rellenar (dejar nulls)")
        choice = input("Elige 1/2/3/4: ").strip()

        s = series.dropna()
        if choice == "1":
            return ("true", True)
        if choice == "2":
            return ("false", False)
        if choice == "3":
            if s.empty:
                print("No hay datos no nulos para calcular moda. Elige True/False.")
                continue
            mode = s.mode(dropna=True)
            if mode.empty:
                print("No se pudo calcular moda. Elige True/False.")
                continue
            return ("mode", bool(mode.iloc[0]))
        if choice == "4":
            return ("none", None)
        print("Opción no válida.")

def ask_imputation_categorical(col: str, series: pd.Series) -> tuple[str, object]:
    while True:
        print("\nRelleno de nulls (columna no numérica):")
        print("  [1] moda (valor más frecuente)")
        print("  [2] constante (lo indicas tú, texto)")
        print("  [3] 'MISSING' (texto literal)")
        print("  [4] cadena vacía ''")
        print("  [5] boolean True")
        print("  [6] boolean False")
        print("  [7] no rellenar (dejar nulls)")
        choice = input("Elige 1/2/3/4/5/6/7: ").strip()

        s = series.dropna()
        if choice == "1":
            if s.empty:
                print("No hay datos no nulos para calcular moda. Elige constante.")
                continue
            mode = s.mode(dropna=True)
            if mode.empty:
                print("No se pudo calcular moda. Elige constante.")
                continue
            return ("mode", str(mode.iloc[0]))
        if choice == "2":
            val = input(f"Valor constante (texto) para '{col}': ").strip()
            return ("constant", val)
        if choice == "3":
            return ("missing_literal", "MISSING")
        if choice == "4":
            return ("empty_string", "")
        if choice == "5":
            return ("true", True)
        if choice == "6":
            return ("false", False)
        if choice == "7":
            return ("none", None)
        print("Opción no válida.")

# ---- NUEVO: cámara y duración ----
def is_camera_col(col: str) -> bool:
    c = col.lower()

    # Elimina cualquier cosa que contenga "camera" o variantes
    camera_keywords = [
        "camera", "camera_settings", "cam_settings", "camerasettings", "camsettings"
    ]
    if any(k in c for k in camera_keywords):
        return True

    # Parámetros típicos de cámara: solo si parece estar bajo settings/jugador (evita falsos positivos)
    cam_params = ["fov", "distance", "height", "angle", "stiffness", "swivel", "transition"]
    if any(p in c for p in cam_params) and ("player" in c or "players" in c) and ("setting" in c or "settings" in c):
        return True

    return False

def find_duration_column(df: pd.DataFrame) -> str | None:
    # 1) candidatos exactos
    for c in DURATION_CANDIDATES:
        if c in df.columns:
            return c
    # 2) fallback: cualquier columna que contenga "duration"
    duration_like = [c for c in df.columns if "duration" in c.lower()]
    if duration_like:
        # preferimos una que parezca seconds si existe
        for c in duration_like:
            if "second" in c.lower():
                return c
        return duration_like[0]
    return None


def main():
    if not os.path.exists(CSV_IN):
        raise FileNotFoundError(f"No existe el archivo: {CSV_IN}")

    df = read_csv_safely(CSV_IN)

    if TREAT_EMPTY_STRINGS_AS_NULL:
        df = df.replace(r"^\s*$", pd.NA, regex=True)

    rows_before_all = len(df)
    cols_before_all = df.shape[1]

    # =========================================================
    # 0) LIMPIEZA AUTOMÁTICA: eliminar columnas de cámara
    # =========================================================
    if DROP_CAMERA_COLUMNS:
        camera_cols = [c for c in df.columns if is_camera_col(c)]
        print("\n========================================")
        print("Eliminación automática: columnas de cámara")
        print("========================================")
        if camera_cols:
            print(f"Columnas detectadas: {len(camera_cols):,}")
            for c in camera_cols:
                print(f"- {c}")
            df = df.drop(columns=camera_cols)
        else:
            print("No se detectaron columnas de cámara con el patrón actual.")

    # =========================================================
    # 1) LIMPIEZA AUTOMÁTICA: eliminar filas con duración < 15s
    # =========================================================
    if DROP_MATCHES_SHORTER_THAN_SECONDS is not None:
        print("\n========================================")
        print(f"Eliminación automática: partidas < {DROP_MATCHES_SHORTER_THAN_SECONDS}s")
        print("========================================")
        dur_col = find_duration_column(df)
        if dur_col is None:
            print("⚠️ No se encontró columna de duración. No se eliminan filas por duración.")
            print("   Columnas que contienen 'duration' en tu CSV:")
            duration_like = [c for c in df.columns if "duration" in c.lower()]
            if duration_like:
                for c in duration_like[:50]:
                    print(f"   - {c}")
                if len(duration_like) > 50:
                    print(f"   ... ({len(duration_like) - 50} más)")
            else:
                print("   (ninguna)")
        else:
            dur = pd.to_numeric(df[dur_col], errors="coerce")
            mask_short = dur.notna() & (dur < DROP_MATCHES_SHORTER_THAN_SECONDS)

            removed_short = int(mask_short.sum())
            df = df.loc[~mask_short].copy()

            print(f"Columna usada: {dur_col}")
            print(f"Filas eliminadas por duración: {removed_short:,}")
            print(f"Filas restantes: {len(df):,}")

    # =========================================================
    # 2) A partir de aquí, tu flujo interactivo de columnas
    # =========================================================
    null_ratio = df.isna().mean()
    keep_set = set(KEEP_COLS)

    candidates = [c for c in df.columns if (null_ratio[c] > THRESHOLD_NULL_RATIO and c not in keep_set)]
    candidates.sort(key=lambda c: null_ratio[c], reverse=True)

    # ===== Mostrar lista de candidatas antes de empezar =====
    print("\n========================================")
    print("Candidatas a revisar (muchos nulos)")
    print(f"Total candidatas (null_ratio > {THRESHOLD_NULL_RATIO}): {len(candidates):,}")
    print("Formato: columna | null_pct | dtype")
    print("========================================")

    if not candidates:
        df.to_csv(CSV_OUT, index=False)
        print("(No hay columnas candidatas. Se guarda copia con la limpieza automática aplicada.)")
        print(f"CSV guardado: {CSV_OUT}")
        print(f"Filas: {len(df):,} | Columnas: {df.shape[1]:,}")
        return

    to_show = candidates if MAX_PRINT_CANDIDATES == 0 else candidates[:MAX_PRINT_CANDIDATES]
    for col in to_show:
        print(f"{col} | {null_ratio[col]*100:.2f}% | {df[col].dtype}")
    if MAX_PRINT_CANDIDATES != 0 and len(candidates) > MAX_PRINT_CANDIDATES:
        print(f"... ({len(candidates) - MAX_PRINT_CANDIDATES} más no mostradas)")

    input("\nPulsa ENTER para empezar a decidir columna por columna...")

    # ===== Interacción =====
    dropped_cols = []
    imputed_cols = {}

    for idx, col in enumerate(candidates, start=1):
        pct = float(null_ratio[col] * 100.0)
        dtype = str(df[col].dtype)

        print(f"\n[{idx}/{len(candidates)}]")

        while True:
            action = ask_action(col, pct, dtype)

            if action == "s":
                print("\nEjemplos (no nulos):")
                print_examples(df[col], n=SHOW_EXAMPLES)
                continue

            if action == "q":
                print("Salida solicitada. No se ha guardado ningún CSV.")
                sys.exit(0)

            if action == "d":
                dropped_cols.append(col)
                break

            if action == "k":
                if is_bool_dtype(df[col].dtype):
                    strat, val = ask_imputation_bool(col, df[col])
                elif is_numeric_dtype(df[col].dtype):
                    strat, val = ask_imputation_numeric(col, df[col])
                else:
                    strat, val = ask_imputation_categorical(col, df[col].astype("string"))

                if strat != "none":
                    df[col] = df[col].fillna(val)

                preview = val
                if isinstance(preview, str):
                    preview = shorten(preview, 60)
                imputed_cols[col] = (strat, preview)
                break

    if dropped_cols:
        df = df.drop(columns=dropped_cols)

    df.to_csv(CSV_OUT, index=False)

    print("\n========================================")
    print("✅ Terminado")
    print(f"CSV guardado: {CSV_OUT}")
    print(f"Filas finales: {len(df):,}")
    print(f"Columnas finales: {df.shape[1]:,}")
    print(f"Columnas eliminadas (interactivo): {len(dropped_cols):,}")
    print(f"Columnas imputadas (rellenadas): {len(imputed_cols):,}")
    print("========================================")


if __name__ == "__main__":
    main()