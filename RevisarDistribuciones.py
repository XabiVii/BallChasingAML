# inspect_distributions_selected_cols_grouped_ranks.py
# - Lee el CSV
# - AGRUPA los ranks quitando la "Division X" y normalizando:
#     "Diamante 1 Division 1/2/3/4" -> "Diamante 1"
#     "Champion 2 Division 1/2/3/4" -> "Champion 2"
#   (funciona también con "Diamond I Division I", etc.)
# - Muestra la distribución de:
#     server.region, min_rank.name, max_rank.name, blue.players.1.id.platform
#
# Ejecuta:
#   python inspect_distributions_selected_cols_grouped_ranks.py

import os
import re
import pandas as pd


# =========================
# CONFIG
# =========================
CSV_PATH = r"replays_2v2_10000_full.csv"  # <- cambia si hace falta

COLUMNS_TO_CHECK = [
    "server.region",
    "min_rank.name",
    "max_rank.name",
    "blue.players.1.id.platform",
]

TOP_N = 30
DROPNA = False                   # False = incluye NaN como categoría
NORMALIZE_EMPTY_STRINGS = True   # "" o "   " -> NA

# Traducción mínima (según lo que pediste):
# "Diamond 1" -> "Diamante 1" (Champion se deja como Champion)
TRANSLATE_DIAMOND_TO_SPANISH = True


# =========================
# HELPERS
# =========================
ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10
}

DIVISION_SUFFIX_RE = re.compile(
    r"\s+(?:division|división|div\.?)\s*(?:\d+|[ivx]+)\s*$",
    flags=re.IGNORECASE
)

# Convierte el numeral del rango (I/II/III) en 1/2/3 si aparece tras la palabra de rango
RANK_ROMAN_RE = re.compile(
    r"\b(Grand\s+Champion|Gran\s+Campe[oó]n|Diamond|Diamante|Champion|Campe[oó]n)\s+(I|II|III|IV|V|VI|VII|VIII|IX|X)\b",
    flags=re.IGNORECASE
)

def read_csv_safely(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def normalize_rank_text(x) -> str:
    """
    Ejemplos que cubre:
      - "Diamante 1 Division 1" -> "Diamante 1"
      - "Champion 2 Division 4" -> "Champion 2"
      - "Diamond I Division III" -> "Diamond 1"
      - "Champion II Division I" -> "Champion 2"
    """
    if pd.isna(x):
        return x

    s = normalize_spaces(str(x))

    # 1) Quitar sufijo de división (Division/División/Div.)
    s = DIVISION_SUFFIX_RE.sub("", s)
    s = normalize_spaces(s)

    # 2) Convertir romano del rango (Diamond I -> Diamond 1, Champion II -> Champion 2, etc.)
    def _roman_repl(m):
        rank_word = m.group(1)
        roman = m.group(2).upper()
        n = ROMAN_TO_INT.get(roman, roman)
        # conservar el texto de rank tal cual venía, pero con número
        return f"{rank_word} {n}"

    s = RANK_ROMAN_RE.sub(_roman_repl, s)
    s = normalize_spaces(s)

    # 3) Si ya viene como "Diamante 1", perfecto. Si viene "Diamond 1" y quieres español:
    if TRANSLATE_DIAMOND_TO_SPANISH:
        # reemplazo seguro de palabra completa
        s = re.sub(r"\bDiamond\b", "Diamante", s, flags=re.IGNORECASE)
        # opcional: capitalizar "Diamante"
        s = re.sub(r"\bdiamante\b", "Diamante", s)

    return s

def print_distribution(series: pd.Series, name: str, top_n: int = 30, dropna: bool = False):
    vc = series.value_counts(dropna=dropna)
    total = len(series)

    print("\n" + "=" * 70)
    print(f"Distribución: {name}")
    print(f"Total filas: {total:,}")
    print(f"Valores no nulos: {series.notna().sum():,}")
    print(f"Nulos: {series.isna().sum():,}")
    print("-" * 70)

    if vc.empty:
        print("(Sin valores para mostrar)")
        return

    head = vc.head(top_n)
    for k, v in head.items():
        label = "<NaN>" if pd.isna(k) else str(k)
        pct = (v / total) * 100.0
        print(f"{label:45}  {v:10,d}  ({pct:6.2f}%)")

    if len(vc) > top_n:
        rest = vc.iloc[top_n:].sum()
        pct_rest = (rest / total) * 100.0
        print("-" * 70)
        print(f"{'__REST__':45}  {rest:10,d}  ({pct_rest:6.2f}%)")

def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"No existe el archivo: {CSV_PATH}")

    df = read_csv_safely(CSV_PATH)

    if NORMALIZE_EMPTY_STRINGS:
        df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Distribuciones, con normalización solo en las columnas de rank
    for col in COLUMNS_TO_CHECK:
        if col not in df.columns:
            print(f"\n❌ Columna no encontrada: {col}")
            close = [c for c in df.columns if col.split(".")[-1].lower() in c.lower()]
            if close:
                print("   ¿Quizá quisiste decir alguna de estas?")
                for c in close[:20]:
                    print(f"   - {c}")
            continue

        s = df[col]

        if col in ("min_rank.name", "max_rank.name"):
            s_norm = s.apply(normalize_rank_text)
            # Muestra ambas distribuciones: original y agrupada
            print_distribution(s, f"{col} (original)", top_n=TOP_N, dropna=DROPNA)
            print_distribution(s_norm, f"{col} (AGRUPADO sin divisiones)", top_n=TOP_N, dropna=DROPNA)
        else:
            print_distribution(s, col, top_n=TOP_N, dropna=DROPNA)

if __name__ == "__main__":
    main()