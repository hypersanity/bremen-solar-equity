"""Aggregate Zensus 2022 100 m grid cells to postcode areas (PLZ) inside Land Bremen,
and build a population-weighted Ortsteil->PLZ crosswalk for Stadt Bremen socio-economic indicators.

Cell assignment: each 100 m cell is assigned to the PLZ polygon containing its centre point
(EPSG:3035 grid centre from GITTER_ID). Counts are summed; rates are re-derived from summed counts
where possible, otherwise weighted means.
"""
import pathlib, json
import numpy as np, pandas as pd, geopandas as gpd

ROOT = pathlib.Path(__file__).resolve().parents[1]
W = ROOT / "work"


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def load(name, cols):
    df = pd.read_csv(W / f"zensus_{name}.csv", dtype=str)
    out = df[["GITTER_ID_100m"]].copy()
    for c in cols:
        out[c] = num(df[c])
    return out.set_index("GITTER_ID_100m")


pop = load("Zensus2022_Bevoelkerungszahl", ["x_mp_100m", "y_mp_100m", "Einwohner"])
hh = load("Zensus2022_Groesse_des_privaten_Haushalts_in_Gitterzellen", ["Insgesamt_Haushalte"])
own = load("Eigentuemerquote_in_Gitterzellen", ["Eigentuemerquote"])
wtyp = load("Wohnungen_nach_Gebaeudetyp_Groesse", ["Insgesamt_Wohnungen", "FreiEFH", "EFH_DHH", "EFH_Reihenhaus", "Freist_ZFH", "ZFH_DHH", "ZFH_Reihenhaus", "MFH_3bis6Wohnungen", "MFH_7bis12Wohnungen", "MFH_13undmehrWohnungen", "AndererGebaeudetyp"])
gtyp = load("Gebaeude_mit_Wohnraum_nach_Gebaeudetyp_Groesse", ["Insgesamt_Gebaeude", "FreiEFH", "EFH_DHH", "EFH_Reihenhaus", "Freist_ZFH", "ZFH_DHH", "ZFH_Reihenhaus"]).add_prefix("geb_")
eig = load("Gebaeude_nach_Eigentumsform_100mGitter", ["Insgesamt_Gebaeude", "Gemeinschaft_Wohneigentuemer", "Privatpersonen", "Wohnungsgenossenschaft", "Kommune_kommunales_Wohnunternehm", "Privatwirtsch_Wohnungsunternehm", "Anderes_privatwirtsch_Unternehm", "Bund_oder_Land", "Organisation_ohne_Erwerbszweck"]).add_prefix("eig_")
rent = load("Zensus2022_Durchschn_Nettokaltmiete", ["durchschnMieteQM"])
age = load("Durchschnittsalter_in_Gitterzellen", ["Durchschnittsalter"])
foreign = load("Auslaenderanteil_in_Gitterzellen", ["AnteilAuslaender"])

g = pop.join([hh, own, wtyp, gtyp, eig, rent, age, foreign], how="outer")
xy = g.index.to_series().str.extract(r"N(\d+)E(\d+)").astype(float)
g["x"] = xy[1] + 50; g["y"] = xy[0] + 50
cells = gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(g.x, g.y), crs=3035).to_crs(25832)

land = gpd.read_file(W / "osm_land_bremen.geojson").to_crs(25832)
plz = gpd.read_file(W / "osm_plz.geojson").to_crs(25832)[["postal_code", "geometry"]]
plz = gpd.overlay(plz, land[["geometry"]], how="intersection")
plz = plz.dissolve("postal_code").reset_index()
plz["area_km2"] = plz.area / 1e6

cells = cells[cells.within(land.union_all())]
cells = gpd.sjoin(cells, plz[["postal_code", "geometry"]], how="left", predicate="within").drop(columns="index_right")

# Ortsteile (Stadt Bremen) + OSM Stadtteile (for naming / Bremerhaven)
ot = gpd.read_file(W / "ortsteile_atlas.gpkg").to_crs(25832)
cells = gpd.sjoin(cells, ot[["ot_id", "ot_name", "stadtteil", "median_income_eur", "sgb2_share", "geometry"]], how="left", predicate="within").drop(columns="index_right")
st = gpd.read_file(W / "osm_admin10.geojson").to_crs(25832)
st["st_label"] = st["name"]
cells = gpd.sjoin(cells, st[["st_label", "geometry"]], how="left", predicate="within").drop(columns="index_right")
cells = cells[~cells.index.duplicated()]

print("cells in Land Bremen:", len(cells), "| unassigned to PLZ:", cells.postal_code.isna().sum(),
      "pop unassigned:", cells.loc[cells.postal_code.isna(), "Einwohner"].sum())

c = cells.copy()
c["hh"] = c["Insgesamt_Haushalte"].fillna(0)
c["pop"] = c["Einwohner"].fillna(0)
# owner-occupied households approximated as quote x households (quote is per occupied dwelling)
c["own_hh"] = c["Eigentuemerquote"] / 100 * c["hh"]
c["own_w"] = np.where(c["Eigentuemerquote"].notna(), c["hh"], 0)
c["dw"] = c["Insgesamt_Wohnungen"].fillna(0)
c["dw_12fam"] = c[["FreiEFH", "EFH_DHH", "EFH_Reihenhaus", "Freist_ZFH", "ZFH_DHH", "ZFH_Reihenhaus"]].fillna(0).sum(axis=1)
c["dw_mfh13"] = c["MFH_13undmehrWohnungen"].fillna(0)
c["dw_mfh"] = c[["MFH_3bis6Wohnungen", "MFH_7bis12Wohnungen", "MFH_13undmehrWohnungen"]].fillna(0).sum(axis=1)
c["bld_12fam"] = c[["geb_FreiEFH", "geb_EFH_DHH", "geb_EFH_Reihenhaus", "geb_Freist_ZFH", "geb_ZFH_DHH", "geb_ZFH_Reihenhaus"]].fillna(0).sum(axis=1)
c["bld"] = c["geb_Insgesamt_Gebaeude"].fillna(0)
for k in ["Gemeinschaft_Wohneigentuemer", "Privatpersonen", "Wohnungsgenossenschaft", "Kommune_kommunales_Wohnunternehm", "Privatwirtsch_Wohnungsunternehm"]:
    c["e_" + k] = c["eig_" + k].fillna(0)
c["e_tot"] = c["eig_Insgesamt_Gebaeude"].fillna(0)
c["rent_w"] = np.where(c["durchschnMieteQM"].notna(), c["dw"] - c["dw"] * c["Eigentuemerquote"].fillna(0) / 100, 0)
c["rent_x"] = c["durchschnMieteQM"].fillna(0) * c["rent_w"]
c["age_x"] = c["Durchschnittsalter"].fillna(0) * np.where(c["Durchschnittsalter"].notna(), c["pop"], 0)
c["age_w"] = np.where(c["Durchschnittsalter"].notna(), c["pop"], 0)
c["for_x"] = c["AnteilAuslaender"].fillna(0) * np.where(c["AnteilAuslaender"].notna(), c["pop"], 0)
c["for_w"] = c["age_w"] * 0 + np.where(c["AnteilAuslaender"].notna(), c["pop"], 0)
c["inc_x"] = c["median_income_eur"].fillna(0) * np.where(c["median_income_eur"].notna(), c["pop"], 0)
c["inc_w"] = np.where(c["median_income_eur"].notna(), c["pop"], 0)
c["sgb_x"] = c["sgb2_share"].fillna(0) * np.where(c["sgb2_share"].notna(), c["pop"], 0)
c["sgb_w"] = np.where(c["sgb2_share"].notna(), c["pop"], 0)

sumcols = ["pop", "hh", "own_hh", "own_w", "dw", "dw_12fam", "dw_mfh", "dw_mfh13", "bld", "bld_12fam", "e_tot",
           "e_Gemeinschaft_Wohneigentuemer", "e_Privatpersonen", "e_Wohnungsgenossenschaft", "e_Kommune_kommunales_Wohnunternehm",
           "e_Privatwirtsch_Wohnungsunternehm", "rent_x", "rent_w", "age_x", "age_w", "for_x", "for_w", "inc_x", "inc_w", "sgb_x", "sgb_w"]
agg = c.groupby("postal_code")[sumcols].sum()
out = pd.DataFrame(index=agg.index)
out["population"] = agg["pop"]
out["households"] = agg["hh"]
out["owner_rate_pct"] = 100 * agg["own_hh"] / agg["own_w"]
out["dwellings"] = agg["dw"]
out["share_dw_1_2_family_pct"] = 100 * agg["dw_12fam"] / agg["dw"]
out["share_dw_mfh13_pct"] = 100 * agg["dw_mfh13"] / agg["dw"]
out["res_buildings"] = agg["bld"]
out["bld_1_2_family"] = agg["bld_12fam"]
out["share_bld_private_person_pct"] = 100 * agg["e_Privatpersonen"] / agg["e_tot"]
out["share_bld_weg_pct"] = 100 * agg["e_Gemeinschaft_Wohneigentuemer"] / agg["e_tot"]
out["share_bld_company_coop_municipal_pct"] = 100 * (agg["e_Wohnungsgenossenschaft"] + agg["e_Kommune_kommunales_Wohnunternehm"] + agg["e_Privatwirtsch_Wohnungsunternehm"]) / agg["e_tot"]
out["net_rent_eur_m2"] = agg["rent_x"] / agg["rent_w"]
out["mean_age"] = agg["age_x"] / agg["age_w"]
out["foreign_pct"] = agg["for_x"] / agg["for_w"]
out["median_income_keur_ot_weighted"] = np.where(agg["inc_w"] > 0.5 * agg["pop"], agg["inc_x"] / agg["inc_w"].replace(0, np.nan), np.nan)
out["sgb2_pct_ot_weighted"] = np.where(agg["sgb_w"] > 0.5 * agg["pop"], agg["sgb_x"] / agg["sgb_w"].replace(0, np.nan), np.nan)
out["income_coverage_pop_share"] = agg["inc_w"] / agg["pop"]

# dominant Stadtteil / Ortsteil names by population
def top_names(df, col, n=3):
    s = df.groupby(col)["pop"].sum().sort_values(ascending=False)
    s = s[s > 0.08 * s.sum()]
    return " / ".join(s.index[:n])
out["stadtteile"] = c.groupby("postal_code").apply(lambda d: top_names(d, "st_label"))
out["ortsteile"] = c.groupby("postal_code").apply(lambda d: top_names(d, "ot_name"))
out = out.join(plz.set_index("postal_code")[["area_km2"]])
out.index.name = "plz"
out.to_csv(W / "plz_zensus.csv")
print(out[["population", "households", "owner_rate_pct", "share_dw_1_2_family_pct", "median_income_keur_ot_weighted", "stadtteile"]].round(1).to_string())
print("TOTAL pop", out.population.sum(), "hh", out.households.sum())
plz.to_file(W / "plz_bremen.gpkg", driver="GPKG")
c[["postal_code", "ot_id", "st_label", "pop", "hh", "geometry"]].to_file(W / "cells_bremen.gpkg", driver="GPKG")
