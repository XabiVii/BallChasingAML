# inspect_distributions_selected_cols_grouped_ranks_with_plots.py
# - Lee el CSV
# - AGRUPA ranks quitando "Division X" y normalizando (Diamond I -> Diamante 1, etc.)
# - Muestra distribuciones en texto
# - CREA PLOTS (barras) para cada distribución y los guarda en ./plots_distributions
#
# Ejecuta:
#   python inspect_distributions_selected_cols_grouped_ranks_with_plots.py

import os
import re
import pandas as pd
import matplotlib.pyplot as plt

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
TRANSLATE_DIAMOND_TO_SPANISH = True

PLOTS_DIR = "plots_distributions"  # carpeta de salida
FIG_DPI = 160

# =========================
# HELPERS (normalización ranks)
# =========================
ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10
}

DIVISION_SUFFIX_RE = re.compile(
    r"\s+(?:division|división|div\.?)\s*(?:\d+|[ivx]+)\s*$",
    flags=re.IGNORECASE
)

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
    if pd.isna(x):
        return x

    s = normalize_spaces(str(x))

    # 1) quitar "Division X"
    s = DIVISION_SUFFIX_RE.sub("", s)
    s = normalize_spaces(s)

    # 2) roman -> int
    def _roman_repl(m):
        rank_word = m.group(1)
        roman = m.group(2).upper()
        n = ROMAN_TO_INT.get(roman, roman)
        return f"{rank_word} {n}"

    s = RANK_ROMAN_RE.sub(_roman_repl, s)
    s = normalize_spaces(s)

    # 3) traducir Diamond -> Diamante
    if TRANSLATE_DIAMOND_TO_SPANISH:
        s = re.sub(r"\bDiamond\b", "Diamante", s, flags=re.IGNORECASE)
        s = re.sub(r"\bdiamante\b", "Diamante", s)

    return s

# =========================
# TEXT + PLOTS
# =========================
def safe_filename(name: str) -> str:
    name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_.\-]+", "_", name)
    return name[:180]

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
        return vc

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

    return vc

def plot_distribution(vc: pd.Series, title: str, out_path: str, top_n: int = 30):
    if vc is None or vc.empty:
        return

    # preparar data para plot (top_n + REST opcional)
    vc_top = vc.head(top_n).copy()
    if len(vc) > top_n:
        rest = vc.iloc[top_n:].sum()
        vc_top.loc["__REST__"] = rest

    labels = [("<NaN>" if pd.isna(x) else str(x)) for x in vc_top.index.tolist()]
    counts = vc_top.values.tolist()

    plt.figure(figsize=(12, 6))
    plt.bar(range(len(counts)), counts)
    plt.xticks(range(len(counts)), labels, rotation=90)
    plt.ylabel("Count")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=FIG_DPI)
    plt.close()

def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"No existe el archivo: {CSV_PATH}")

    os.makedirs(PLOTS_DIR, exist_ok=True)

    df = read_csv_safely(CSV_PATH)

    if NORMALIZE_EMPTY_STRINGS:
        df = df.replace(r"^\s*$", pd.NA, regex=True)

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

        # ranks: plot original + agrupado
        if col in ("min_rank.name", "max_rank.name"):
            s_norm = s.apply(normalize_rank_text)

            vc1 = print_distribution(s, f"{col} (original)", top_n=TOP_N, dropna=DROPNA)
            plot_distribution(
                vc1,
                title=f"{col} (original) — Top {TOP_N}",
                out_path=os.path.join(PLOTS_DIR, f"{safe_filename(col)}_original.png"),
                top_n=TOP_N
            )

            vc2 = print_distribution(s_norm, f"{col} (Grouped without divisions)", top_n=TOP_N, dropna=DROPNA)
            plot_distribution(
                vc2,
                title=f"{col} (Grouped without divisions) — Top {TOP_N}",
                out_path=os.path.join(PLOTS_DIR, f"{safe_filename(col)}_grouped.png"),
                top_n=TOP_N
            )
        else:
            vc = print_distribution(s, col, top_n=TOP_N, dropna=DROPNA)
            plot_distribution(
                vc,
                title=f"{col} — Top {TOP_N}",
                out_path=os.path.join(PLOTS_DIR, f"{safe_filename(col)}.png"),
                top_n=TOP_N
            )

    print(f"\n✅ PLOTS guardados en: {os.path.abspath(PLOTS_DIR)}")

if __name__ == "__main__":
    main()