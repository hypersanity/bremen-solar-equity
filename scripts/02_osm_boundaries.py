"""Fetch boundaries from OpenStreetMap (Overpass): postcode polygons, Land Bremen, Stadtteile/Ortsteile.

Writes GeoJSON in EPSG:4326 to work/.
OSM data (c) OpenStreetMap contributors, ODbL 1.0.
"""
import json, pathlib, time, urllib.request, urllib.parse
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import polygonize, unary_union

WORK = pathlib.Path(__file__).resolve().parents[1] / "work"
UA = {"User-Agent": "bremen-solar-equity-study/1.0 (research; contact via OSM)", "Accept": "*/*"}
EP = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def overpass(q):
    for attempt in range(6):
        ep = EP[attempt % len(EP)]
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except Exception as e:
            print("retry", ep, e); time.sleep(10)
    raise RuntimeError("overpass failed")


def rel_to_gdf(data, keep):
    rows = []
    for el in data["elements"]:
        if el["type"] != "relation":
            continue
        lines = []
        for m in el.get("members", []):
            if m["type"] == "way" and m.get("role", "outer") in ("outer", "") and "geometry" in m:
                lines.append(LineString([(p["lon"], p["lat"]) for p in m["geometry"]]))
        polys = list(polygonize(unary_union(lines)))
        if not polys:
            continue
        geom = unary_union(polys)
        tags = el.get("tags", {})
        rows.append({"osm_id": el["id"], **{k: tags.get(k) for k in keep}, "geometry": geom})
    return gpd.GeoDataFrame(rows, crs=4326)


# Land Bremen = relation 62718 (Freie Hansestadt Bremen, admin_level 4)
q_land = '[out:json][timeout:240];rel["boundary"="administrative"]["admin_level"="4"]["name"="Bremen"];out geom;'
land = rel_to_gdf(overpass(q_land), ["name", "admin_level", "de:amtlicher_gemeindeschluessel"])
land.to_file(WORK / "osm_land_bremen.geojson", driver="GeoJSON")
print("land", len(land), land.area.sum())

q_plz = '[out:json][timeout:240];area["boundary"="administrative"]["admin_level"="4"]["name"="Bremen"]->.a;rel["boundary"="postal_code"](area.a);out geom;'
plz = rel_to_gdf(overpass(q_plz), ["postal_code", "note", "name"])
plz.to_file(WORK / "osm_plz.geojson", driver="GeoJSON")
print("plz", len(plz), sorted(plz.postal_code.dropna())[:80])

for lvl in ("9", "10"):
    q = f'[out:json][timeout:240];area["boundary"="administrative"]["admin_level"="4"]["name"="Bremen"]->.a;rel["boundary"="administrative"]["admin_level"="{lvl}"](area.a);out geom;'
    g = rel_to_gdf(overpass(q), ["name", "admin_level", "ref"])
    g.to_file(WORK / f"osm_admin{lvl}.geojson", driver="GeoJSON")
    print("admin", lvl, len(g), list(g.name)[:100])
