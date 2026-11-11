"""Validation checks: (1) grid totals vs official Zensus Gemeinde totals; (2) grid-derived owner rate per Ortsteil
vs the Ortsteilatlas' published GWZ-2022 Eigentümerquote; (3) sensitivity of the PLZ ranking to the ROOF definition."""
import pathlib, json
import numpy as np, pandas as pd, geopandas as gpd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
W = ROOT / "work"; OUT = ROOT / "out"
V = {}
z = pd.read_csv(W / "plz_zensus.csv", dtype={"plz": str})
V["grid_pop_total"] = int(z.population.sum()); V["official_pop_total_Land"] = 693204
V["grid_hh_total"] = int(z.households.sum()); V["official_hh_total_Land"] = 349406
V["pop_ratio"] = round(V["grid_pop_total"] / 693204, 4); V["hh_ratio"] = round(V["grid_hh_total"] / 349406, 4)

# owner rate per Ortsteil from grid
cells = pd.read_csv(W / "zensus_Eigentuemerquote_in_Gitterzellen.csv", dtype=str)
cells["q"] = pd.to_numeric(cells.Eigentuemerquote.str.replace(",", "."), errors="coerce")
hh = pd.read_csv(W / "zensus_Zensus2022_Groesse_des_privaten_Haushalts_in_Gitterzellen.csv", dtype=str)
hh["h"] = pd.to_numeric(hh.Insgesamt_Haushalte, errors="coerce")
c = cells.merge(hh[["GITTER_ID_100m", "h"]], on="GITTER_ID_100m")
xy = c.GITTER_ID_100m.str.extract(r"N(\d+)E(\d+)").astype(float)
g = gpd.GeoDataFrame(c, geometry=gpd.points_from_xy(xy[1] + 50, xy[0] + 50), crs=3035).to_crs(25832)
ot = gpd.read_file(W / "ortsteile_atlas.gpkg").to_crs(25832)
g = gpd.sjoin(g, ot[["ot_id", "owner_rate_2022_atlas", "geometry"]], predicate="within")
g = g.dropna(subset=["q", "h"])
a = g.assign(x=g.q * g.h).groupby("ot_id").agg(x=("x", "sum"), h=("h", "sum"), atlas=("owner_rate_2022_atlas", "first"))
a["grid"] = a.x / a.h
a = a[(a.h > 200) & a.atlas.notna()]
r, p = stats.pearsonr(a.grid, a.atlas)
V["owner_rate_ortsteil_validation"] = dict(n=len(a), pearson_r=round(r, 3), mean_abs_diff_pp=round(float((a.grid - a.atlas).abs().mean()), 2),
                                           median_diff_pp=round(float((a.grid - a.atlas).median()), 2))

# sensitivity: alternative ROOF definitions
d = pd.read_csv(W / "mastr_solar_bremen.csv", dtype=str); d["kw"] = pd.to_numeric(d.Bruttoleistung)
op = d[d.EinheitBetriebsstatus == "35"]
m = pd.read_csv(OUT / "plz_metrics.csv", dtype={"plz": str}).set_index("plz")
alts = {
    "A_haushalt_le30": op[(op.ArtDerSolaranlage == "853") & (op.Nutzungsbereich == "713") & (op.kw <= 30)],
    "B_all_building_pv_le30_any_use": op[(op.ArtDerSolaranlage == "853") & (op.kw <= 30)],
    "C_haushalt_incl_planned": d[(d.ArtDerSolaranlage == "853") & (d.Nutzungsbereich == "713") & d.EinheitBetriebsstatus.isin(["35", "31"])],
}
sens = {}
for k, s in alts.items():
    rate = 1000 * s.groupby("Postleitzahl").size().reindex(m.index).fillna(0) / m.households
    rho, _ = stats.spearmanr(rate, m.roof_per_1k_hh)
    rho_own, _ = stats.spearmanr(rate, m.owner_rate_pct)
    sens[k] = dict(units=int(len(s)), spearman_vs_main=round(rho, 3), spearman_vs_owner_rate=round(rho_own, 2),
                   top5=list(rate.sort_values(ascending=False).index[:5]), bottom5=list(rate.sort_values().index[:5]))
sens["main"] = dict(top5=list(m.roof_per_1k_hh.sort_values(ascending=False).index[:5]), bottom5=list(m.roof_per_1k_hh.sort_values().index[:5]))
V["sensitivity"] = sens
json.dump(V, open(OUT / "validation.json", "w"), indent=1)
print(json.dumps(V, indent=1))
