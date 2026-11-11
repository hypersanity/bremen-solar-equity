"""Filter Zensus 2022 100 m grid CSVs to a bounding box around Land Bremen (EPSG:3035).

Output: work/zensus_<name>.csv with only cells whose centroid falls in the bbox.
The exact clip to the Land Bremen polygon happens later in the join step.
"""
import zipfile, io, sys, pathlib
import pandas as pd
from pyproj import Transformer

RAW = pathlib.Path(__file__).resolve().parents[1] / "raw" / "zensus"
WORK = pathlib.Path(__file__).resolve().parents[1] / "work"
WORK.mkdir(exist_ok=True)

t = Transformer.from_crs(4326, 3035, always_xy=True)
xs, ys = zip(*[t.transform(lon, lat) for lon in (8.40, 9.05) for lat in (52.98, 53.65)])
XMIN, XMAX, YMIN, YMAX = min(xs) - 500, max(xs) + 500, min(ys) - 500, max(ys) + 500
print("bbox 3035", XMIN, XMAX, YMIN, YMAX)

for z in sorted(RAW.glob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        member = [n for n in zf.namelist() if n.endswith(".csv") and "100m" in n][0]
        out = WORK / f"zensus_{z.stem}.csv"
        if out.exists():
            print("skip", out.name); continue
        parts = []
        with zf.open(member) as fh:
            for chunk in pd.read_csv(fh, sep=";", encoding="latin-1", chunksize=500_000,
                                     dtype=str, decimal=","):
                if "x_mp_100m" not in chunk:
                    xy = chunk["GITTER_ID_100m"].str.extract(r"N(\d+)E(\d+)").astype(int)
                    chunk["x_mp_100m"] = (xy[1] + 50).astype(str); chunk["y_mp_100m"] = (xy[0] + 50).astype(str)
                x = pd.to_numeric(chunk["x_mp_100m"]); y = pd.to_numeric(chunk["y_mp_100m"])
                parts.append(chunk[(x >= XMIN) & (x <= XMAX) & (y >= YMIN) & (y <= YMAX)])
        df = pd.concat(parts)
        df.to_csv(out, index=False)
        print(z.stem, member, len(df), list(df.columns))
