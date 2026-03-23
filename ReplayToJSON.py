import os
import csv
import json
from collections.abc import Mapping

import ballchasing
from ballchasing import Rank

# =========================
# CONFIG
# =========================
TOKEN = os.environ["BALLCHASING_TOKEN"]
api = ballchasing.Api(TOKEN, print_on_rate_limit=True)

COUNT = 10_000
DATASETS_DIR = "datasets"
OUT_CSV = os.path.join(DATASETS_DIR, "replays_2v2_10000_full.csv")
TMP_JSONL = os.path.join(DATASETS_DIR, "tmp_replays_flat_full.jsonl")

os.makedirs(DATASETS_DIR, exist_ok=True)

# =========================
# FLATTEN TOTAL (sin recortes)
# =========================
def to_scalar(x):
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    # Cualquier cosa rara -> string JSON
    try:
        return json.dumps(x, ensure_ascii=False)
    except Exception:
        return str(x)

def flatten_all(obj, parent_key="", sep="."):
    """
    Aplana TODO el JSON:
    - dict -> parent.key
    - list/tuple -> parent.0, parent.1, ...
    - valores -> celda scalar
    """
    out = {}

    if isinstance(obj, Mapping):
        for k, v in obj.items():
            k = str(k)
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            out.update(flatten_all(v, new_key, sep))
        return out

    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            out.update(flatten_all(v, new_key, sep))
        return out

    # Primitivo / final
    if parent_key:
        out[parent_key] = to_scalar(obj)
    else:
        out["value"] = to_scalar(obj)

    return out

# =========================
# 1) DESCARGAR REPLAYS 2v2 + APLANAR A JSONL (streaming)
# =========================
replays = api.get_replays(
    min_rank=Rank.SILVER_1,
    max_rank=Rank.GRAND_CHAMPION_3,
    playlist=ballchasing.Playlist.RANKED_DOUBLES,  # ✅ 2v2
    count=COUNT,
    deep=True  # ✅ toda la info disponible en la API (stats completas)
)

all_columns = set()
rows_written = 0

with open(TMP_JSONL, "w", encoding="utf-8") as tmp:
    for i, replay in enumerate(replays, start=1):
        flat = flatten_all(replay)

        all_columns.update(flat.keys())
        tmp.write(json.dumps(flat, ensure_ascii=False) + "\n")
        rows_written += 1

        if i % 200 == 0:
            print(f"Procesados {i}/{COUNT} replays | columnas únicas: {len(all_columns)}")

print(f"✔ Replays aplanados guardados (JSONL): {rows_written}")
print(f"✔ Columnas totales detectadas: {len(all_columns)}")

# =========================
# 2) ESCRIBIR CSV FINAL con TODAS las columnas
# =========================
fieldnames = sorted(all_columns)

with open(OUT_CSV, "w", newline="", encoding="utf-8") as fcsv:
    writer = csv.DictWriter(
        fcsv,
        fieldnames=fieldnames,
        extrasaction="ignore",
        restval=""
    )
    writer.writeheader()

    with open(TMP_JSONL, "r", encoding="utf-8") as tmp:
        for n, line in enumerate(tmp, start=1):
            row = json.loads(line)
            writer.writerow(row)

            if n % 500 == 0:
                print(f"CSV: escritas {n}/{rows_written} filas")

print(f"\n✅ CSV generado: {OUT_CSV}")
print(f"✅ Temporal JSONL: {TMP_JSONL}")