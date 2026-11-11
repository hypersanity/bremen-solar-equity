"""Interactive Leaflet map (folium): rooftop and plug-in PV per 1,000 households + context layers, popups per PLZ."""
import pathlib
import pandas as pd, geopandas as gpd, folium
from branca.colormap import StepColormap

ROOT = pathlib.Path(__file__).resolve().parents[1]
W = ROOT / "work"; OUT = ROOT / "out"
m = pd.read_csv(OUT / "plz_metrics.csv", dtype={"plz": str}).set_index("plz")
g = gpd.read_file(W / "plz_bremen.gpkg").set_index("postal_code")[["geometry"]].join(m, how="inner").reset_index(names="plz").to_crs(4326)
g["geometry"] = g.geometry.simplify(0.0001)
keep = ["plz", "stadtteile", "households", "roof_units", "roof_per_1k_hh", "roof_W_per_hh", "plug_units", "plug_per_1k_hh",
        "owner_rate_pct", "share_dw_1_2_family_pct", "median_income_keur_ot_weighted", "geometry"]
g = g[keep].copy()
for c in ["roof_per_1k_hh", "plug_per_1k_hh", "owner_rate_pct", "share_dw_1_2_family_pct", "median_income_keur_ot_weighted", "roof_W_per_hh"]:
    g[c] = g[c].round(1)
g["households"] = g.households.astype(int)

BREAKS = [0, 10, 20, 30, 45, 70, 120]
COLS = ["#fff7bc", "#fee391", "#fec44f", "#fe9929", "#d95f0e", "#8c2d04"]
cm = StepColormap(COLS, index=BREAKS, vmin=0, vmax=120, caption="PV units per 1,000 households (both layers)")

fmap = folium.Map(location=[53.2, 8.75], zoom_start=10, tiles="OpenStreetMap", control_scale=True)
tip = folium.GeoJsonTooltip(fields=["plz", "stadtteile", "households", "roof_units", "roof_per_1k_hh", "plug_units", "plug_per_1k_hh",
                                    "owner_rate_pct", "share_dw_1_2_family_pct", "median_income_keur_ot_weighted"],
                            aliases=["PLZ", "Stadtteil(e)", "Households (Zensus 2022)", "Rooftop units", "Rooftop / 1,000 hh", "Plug-in units",
                                     "Plug-in / 1,000 hh", "Owner-occupancy %", "Dwellings in 1–2-family houses %", "Median income k€ (2020)"], localize=True)
for col, name, show in [("roof_per_1k_hh", "Rooftop PV per 1,000 households", True), ("plug_per_1k_hh", "Plug-in PV per 1,000 households", False)]:
    folium.GeoJson(g.to_json(), name=name, show=show,
                   style_function=lambda f, col=col: {"fillColor": cm(min(f["properties"][col], 119)), "color": "white", "weight": 1, "fillOpacity": 0.8},
                   highlight_function=lambda f: {"weight": 3, "color": "#333"},
                   tooltip=folium.GeoJsonTooltip(fields=tip.fields, aliases=tip.aliases, localize=True)).add_to(fmap)
cm.add_to(fmap)
folium.LayerControl(collapsed=False).add_to(fmap)
title = ('<div style="position:fixed;top:10px;left:60px;z-index:9999;background:white;padding:6px 10px;border:1px solid #999;font:14px sans-serif">'
         '<b>Solar equity in Land Bremen</b> — residential PV units per 1,000 households by postcode<br>'
         '<span style="font-size:11px">MaStR export 2026-11-08 (BNetzA, dl-de/by-2-0) · Zensus 2022 (Destatis) · PLZ © OpenStreetMap (ODbL) · income: Bremer Ortsteilatlas</span></div>')
fmap.get_root().html.add_child(folium.Element(title))
fmap.fit_bounds([[53.0, 8.48], [53.61, 8.99]])
fmap.save(str(OUT / "bremen_solar_equity_map.html"))
print("saved", OUT / "bremen_solar_equity_map.html")
