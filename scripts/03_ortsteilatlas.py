"""Extract Bremen Ortsteil indicators + polygons from the official Bremer Ortsteilatlas
(Statistisches Landesamt Bremen, https://www.statistik-bremen.de/tabellen/kleinraum/ortsteilatlas/atlas.html).

Indicators: median income of income-tax payers (latest year), SGB II recipients (latest),
Eigentümerquote 2022, households. Polygons: decode the atlas' delta-encoded pixel geometry
(EPSG:3857 bounding box given in the file) and validate against OSM Stadtteile.
"""
import json, re, pathlib, urllib.request
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid

ROOT = pathlib.Path(__file__).resolve().parents[1]
A = ROOT / "raw" / "ortsteilatlas"
BASE = "https://www.statistik-bremen.de/tabellen/kleinraum/ortsteilatlas/"
d = json.load(open(A / "data.js", encoding="utf-8-sig"))
g = d["geographies"][0]
feats = g["features"]
ids = [f["id"] for f in feats]

WANT = {"i162": "median_income_eur", "i154": "sgb2_share", "i127": "owner_rate_2022_atlas"}
rows = {i: {"ot_id": i, "ot_name": f["name"], "stadtteil": f["filters"][0]["name"]} for i, f in zip(ids, feats)}
meta = {}
for t in g["themes"]:
    if not any(ind["id"] in WANT for ind in t["indicators"]):
        continue
    fn = t["fileName"].lstrip("./")
    p = A / fn.split("?")[0]
    if not p.exists():
        urllib.request.urlretrieve(BASE + fn, p)
    td = json.load(open(p, encoding="utf-8-sig"))
    for ind in td["indicators"]:
        if ind["id"] in WANT:
            col = WANT[ind["id"]]
            # keep latest date
            if col in meta and meta[col]["date"] >= ind["date"]:
                continue
            props = {x["name"]: x["value"] for x in ind.get("properties", [])}
            meta[col] = {"date": ind["date"], "name": ind["name"], "metatext": re.sub("<[^>]+>", " ", props.get("metatext", ""))[:400]}
            for i, v in zip(ids, ind["values"]):
                try:
                    rows[i][col] = float(v)
                except (TypeError, ValueError):
                    rows[i][col] = None
print(json.dumps(meta, ensure_ascii=False, indent=1))

# ---- geometry ----
s = open(A / "_hb_ortsteile_20130116_project_neu.shp1.js", encoding="utf-8-sig").read()
gj = json.loads(s)
minx, miny, maxx, maxy = map(float, gj["boundingBox"].split())
pw, ph = gj["pixelWidth"], gj["pixelHeight"]
sx, sy = (maxx - minx) / pw, (maxy - miny) / ph


def ring(arr):
    x, y = arr[0], arr[1]
    pts = [(x, y)]
    for k in range(2, len(arr) - 1, 2):
        x += arr[k]; y += arr[k + 1]
        pts.append((x, y))
    return [(minx + px * sx, miny + py * sy) for px, py in pts]


geo = []
for f in gj["features"]:
    rings = [ring(r) for r in f["p"] if len(r) >= 6]
    polys = [Polygon(r) for r in rings if len(r) >= 3]
    # largest = outer; treat others by containment
    polys.sort(key=lambda p: -p.area)
    out = []
    for p in polys:
        hole_of = next((o for o in out if o.contains(p.representative_point())), None)
        if hole_of is not None:
            out[out.index(hole_of)] = hole_of.difference(p)
        else:
            out.append(p)
    geo.append({"ot_id": f["d"], "geometry": make_valid(MultiPolygon([q for o in out for q in (o.geoms if hasattr(o, 'geoms') else [o])]))})
gdf = gpd.GeoDataFrame(geo, crs=3857).dissolve("ot_id").reset_index()
import pandas as pd
att = pd.DataFrame(rows.values())
gdf = gdf.merge(att, on="ot_id", how="left").to_crs(25832)
print(len(gdf), "ortsteile; area km2", round(gdf.area.sum() / 1e6, 1))

# validation against OSM Stadtteile (admin_level 10), Stadt Bremen only
osm = gpd.read_file(ROOT / "work" / "osm_admin10.geojson").to_crs(25832)
st = gdf.dissolve("stadtteil").reset_index()
res = []
for _, r in st.iterrows():
    m = osm[(osm.name == r.stadtteil) & (osm.geometry.centroid.y < 5900000)]
    if len(m) == 0:
        continue
    o = m.geometry.union_all()
    iou = r.geometry.intersection(o).area / r.geometry.union(o).area
    res.append((r.stadtteil, round(iou, 3)))
print("IoU atlas-stadtteil vs OSM:", sorted(res, key=lambda x: x[1]))
gdf.to_file(ROOT / "work" / "ortsteile_atlas.gpkg", driver="GPKG")
json.dump(meta, open(ROOT / "work" / "ortsteile_atlas_meta.json", "w"), ensure_ascii=False, indent=1)
