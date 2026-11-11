"""PLZ-level residential solar metrics for Land Bremen + equity statistics.

Definitions (fixed before looking at PLZ results; see methodology section of the report):
  ROOF  = MaStR EinheitSolar, ArtDerSolaranlage 853 'Gebäudesolaranlage', Nutzungsbereich 713 'Haushalt',
          EinheitBetriebsstatus 35 'In Betrieb'. All sizes; <=30 kWp subset reported separately.
  PLUG  = ArtDerSolaranlage 2961 'Steckerfertige Solaranlage (sog. Balkonkraftwerk)', status 'In Betrieb'.
  Denominator = Zensus 2022 private households in the PLZ (100 m grid, centre-point assignment).
"""
import pathlib, json
import numpy as np, pandas as pd, geopandas as gpd
from scipy import stats
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
W = ROOT / "work"; OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)

k = pd.read_csv(W / "mastr_katalog.csv", dtype=str); lab = dict(zip(k.Id, k.Wert))
d = pd.read_csv(W / "mastr_solar_bremen.csv", dtype=str)
d["kw"] = pd.to_numeric(d.Bruttoleistung)
d["date"] = pd.to_datetime(d.Inbetriebnahmedatum, errors="coerce")
z = pd.read_csv(W / "plz_zensus.csv", dtype={"plz": str}).set_index("plz")

# ---- filtering funnel (reported in the methodology) ----
funnel = [("All solar units, Gemeindeschlüssel Bremen/Bremerhaven", len(d))]
op = d[d.EinheitBetriebsstatus == "35"]; funnel.append(("… in operation (In Betrieb)", len(op)))
roof_all = op[op.ArtDerSolaranlage == "853"]; funnel.append(("… building-mounted (Gebäudesolaranlage)", len(roof_all)))
roof = roof_all[roof_all.Nutzungsbereich == "713"]; funnel.append(("… of which use 'Haushalt' = ROOF", len(roof)))
plug = op[op.ArtDerSolaranlage == "2961"]; funnel.append(("Plug-in units in operation = PLUG", len(plug)))
excluded = roof_all[roof_all.Nutzungsbereich != "713"].Nutzungsbereich.map(lambda x: lab.get(x, "missing")).value_counts()
roof = roof[roof.Postleitzahl.isin(z.index)]; plug = plug[plug.Postleitzahl.isin(z.index)]
funnel.append(("ROOF with PLZ inside Land Bremen polygons", len(roof)))
funnel.append(("PLUG with PLZ inside Land Bremen polygons", len(plug)))
pd.DataFrame(funnel, columns=["step", "units"]).to_csv(OUT / "funnel.csv", index=False)
excluded.to_csv(OUT / "excluded_building_pv_by_use.csv")
print(pd.DataFrame(funnel).to_string()); print("excluded building PV by use:\n", excluded.to_string())

g = pd.DataFrame(index=z.index)
g["roof_units"] = roof.groupby("Postleitzahl").size()
g["roof_kw"] = roof.groupby("Postleitzahl").kw.sum()
g["roof_units_le30"] = roof[roof.kw <= 30].groupby("Postleitzahl").size()
g["roof_units_gt30"] = roof[roof.kw > 30].groupby("Postleitzahl").size()
g["roof_units_2023plus"] = roof[roof.date >= "2023-01-01"].groupby("Postleitzahl").size()
g["roof_battery_share"] = roof.assign(b=(roof.SpeicherAmGleichenOrt == "1").astype(float)).groupby("Postleitzahl").b.mean()
g["plug_units"] = plug.groupby("Postleitzahl").size()
g["plug_kw"] = plug.groupby("Postleitzahl").kw.sum()
g = g.fillna({c: 0 for c in g.columns if c != "roof_battery_share"})
m = z.join(g)
hh = m.households
m["roof_per_1k_hh"] = 1000 * m.roof_units / hh
m["plug_per_1k_hh"] = 1000 * m.plug_units / hh
m["all_per_1k_hh"] = 1000 * (m.roof_units + m.plug_units) / hh
m["roof_W_per_hh"] = 1000 * m.roof_kw / hh
m["roof_le30_per_100_12fam_bld"] = 100 * m.roof_units_le30 / m.bld_1_2_family
m["roof_2023plus_per_1k_hh"] = 1000 * m.roof_units_2023plus / hh
m["plug_share_of_all_pct"] = 100 * m.plug_units / (m.roof_units + m.plug_units)
m["city"] = np.where(m.index.str.startswith("275"), "Bremerhaven", "Bremen")
m.to_csv(OUT / "plz_metrics.csv")

# ---- headline numbers ----
H = {}
for city, s in [("Land Bremen", m), ("Stadt Bremen (PLZ 28xxx)", m[m.city == "Bremen"]), ("Bremerhaven (PLZ 275xx)", m[m.city == "Bremerhaven"])]:
    H[city] = dict(households=int(s.households.sum()), roof_units=int(s.roof_units.sum()), roof_kw=round(s.roof_kw.sum(), 1),
                   plug_units=int(s.plug_units.sum()), roof_per_1k=round(1000 * s.roof_units.sum() / s.households.sum(), 1),
                   plug_per_1k=round(1000 * s.plug_units.sum() / s.households.sum(), 1),
                   roof_W_per_hh=round(1000 * s.roof_kw.sum() / s.households.sum(), 1))
H["roof_battery_share_overall"] = round(float((roof.SpeicherAmGleichenOrt == "1").mean()), 3)
H["roof_median_kw"] = round(float(roof.kw.median()), 2)
H["plug_median_kw"] = round(float(plug.kw.median()), 2)
H["roof_gt30_units"] = int((roof.kw > 30).sum()); H["roof_gt30_kw"] = round(float(roof[roof.kw > 30].kw.sum()), 1)
H["mastr_snapshot"] = "Gesamtdatenexport 2026-11-08"
r = m.roof_per_1k_hh
H["roof_per_1k_range"] = [round(r.min(), 1), r.idxmin(), round(r.max(), 1), r.idxmax()]
H["roof_max_min_ratio"] = round(r.max() / r.min(), 1)
p = m.plug_per_1k_hh
H["plug_per_1k_range"] = [round(p.min(), 1), p.idxmin(), round(p.max(), 1), p.idxmax()]
H["plug_max_min_ratio"] = round(p.max() / p.min(), 1)


# ---- inequality: household-weighted Gini & concentration indices ----
def gini_weighted(x, w):
    o = np.argsort(x); x, w = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(w) / w.sum(); cx = np.cumsum(x * w) / (x * w).sum()
    cw = np.r_[0, cw]; cx = np.r_[0, cx]
    return 1 - np.sum((cw[1:] - cw[:-1]) * (cx[1:] + cx[:-1])), cw, cx


def conc_index(x, rank_by, w):
    o = np.argsort(rank_by); x, w = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.r_[0, np.cumsum(w) / w.sum()]; cx = np.r_[0, np.cumsum(x * w) / (x * w).sum()]
    return 1 - np.sum((cw[1:] - cw[:-1]) * (cx[1:] + cx[:-1])), cw, cx


curves = {}
for var in ["roof_per_1k_hh", "plug_per_1k_hh"]:
    gi, cw, cx = gini_weighted(m[var].values, m.households.values)
    H[f"gini_{var}"] = round(gi, 3); curves[f"lorenz_{var}"] = (cw.tolist(), cx.tolist())
hb = m[m.city == "Bremen"].dropna(subset=["median_income_keur_ot_weighted"])
for var in ["roof_per_1k_hh", "plug_per_1k_hh"]:
    ci, cw, cx = conc_index(hb[var].values, hb.median_income_keur_ot_weighted.values, hb.households.values)
    H[f"CI_income_{var}"] = round(ci, 3); curves[f"conc_income_{var}"] = (cw.tolist(), cx.tolist())
    ci2, cw2, cx2 = conc_index(m[var].values, m.owner_rate_pct.values, m.households.values)
    H[f"CI_owner_{var}"] = round(ci2, 3); curves[f"conc_owner_{var}"] = (cw2.tolist(), cx2.tolist())
json.dump(curves, open(OUT / "curves.json", "w"))

# ---- correlations (Spearman, n = PLZ) ----
expl = {"owner_rate_pct": "Owner-occupancy rate (%)", "share_dw_1_2_family_pct": "Dwellings in 1–2-family houses (%)",
        "share_dw_mfh13_pct": "Dwellings in 13+ unit blocks (%)", "share_bld_company_coop_municipal_pct": "Buildings owned by housing companies/co-ops/municipal (%)",
        "median_income_keur_ot_weighted": "Median taxable income (k€, 2020)*", "sgb2_pct_ot_weighted": "SGB II recipients (% <65, 2024)*",
        "net_rent_eur_m2": "Mean net cold rent (€/m²)", "mean_age": "Mean age (years)", "foreign_pct": "Foreign nationals (%)"}
rows = []
for col, name in expl.items():
    for y in ["roof_per_1k_hh", "plug_per_1k_hh", "roof_le30_per_100_12fam_bld"]:
        s = m[[col, y]].dropna()
        rho, pv = stats.spearmanr(s[col], s[y])
        rows.append(dict(variable=name, outcome=y, n=len(s), rho=round(rho, 2), p=round(pv, 4)))
corr = pd.DataFrame(rows)
corr.to_csv(OUT / "correlations.csv", index=False)
print(corr.pivot(index="variable", columns="outcome", values="rho").to_string())
print(corr.pivot(index="variable", columns="outcome", values="p").to_string())

# ---- OLS on standardised variables, Stadt Bremen (income available) ----
models = {}
def ols(df, y, xs, name):
    s = df[[y] + xs].dropna()
    Z = (s - s.mean()) / s.std()
    X = sm.add_constant(Z[xs]); res = sm.OLS(Z[y], X).fit(cov_type="HC3")
    vif = {x: round(1 / (1 - sm.OLS(Z[x], sm.add_constant(Z[[v for v in xs if v != x]])).fit().rsquared), 2) if len(xs) > 1 else 1.0 for x in xs}
    models[name] = dict(n=int(res.nobs), r2=round(res.rsquared, 3), coefs={x: [round(res.params[x], 3), round(res.pvalues[x], 4)] for x in xs}, vif=vif)
ols(hb, "roof_per_1k_hh", ["share_dw_1_2_family_pct", "median_income_keur_ot_weighted"], "roof ~ 1-2fam + income (Stadt Bremen)")
ols(hb, "roof_per_1k_hh", ["owner_rate_pct", "median_income_keur_ot_weighted"], "roof ~ owner + income (Stadt Bremen)")
ols(hb, "plug_per_1k_hh", ["share_dw_1_2_family_pct", "median_income_keur_ot_weighted"], "plug ~ 1-2fam + income (Stadt Bremen)")
ols(hb, "roof_le30_per_100_12fam_bld", ["median_income_keur_ot_weighted"], "roof per 100 1-2fam bld ~ income (Stadt Bremen)")
ols(m.assign(bhv=(m.city == "Bremerhaven").astype(float)), "roof_per_1k_hh", ["share_dw_1_2_family_pct", "bhv"], "roof ~ 1-2fam + Bremerhaven dummy (Land)")
json.dump(models, open(OUT / "models.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(models, indent=1, ensure_ascii=False))

# ---- quintile table (PLZ ranked by owner-occupancy, household-weighted quintiles) ----
def wq(df, col, q=5):
    s = df.sort_values(col); cs = s.households.cumsum() / s.households.sum()
    return pd.Series(np.minimum((cs * q - 1e-9).astype(int) + 1, q), index=s.index)
for col, tag in [("owner_rate_pct", "owner"), ("median_income_keur_ot_weighted", "income")]:
    base = m if tag == "owner" else hb
    qq = wq(base, col)
    t = base.assign(q=qq).groupby("q").agg(plz=("households", "size"), households=("households", "sum"), x_min=(col, "min"), x_max=(col, "max"),
                                           roof=("roof_units", "sum"), plug=("plug_units", "sum"), roof_kw=("roof_kw", "sum"))
    t["roof_per_1k_hh"] = (1000 * t.roof / t.households).round(1)
    t["plug_per_1k_hh"] = (1000 * t.plug / t.households).round(1)
    t["roof_W_per_hh"] = (1000 * t.roof_kw / t.households).round(0)
    t.to_csv(OUT / f"quintiles_{tag}.csv")
    print(tag, "\n", t.to_string())
    H[f"q5_q1_ratio_roof_{tag}"] = round(t.roof_per_1k_hh.iloc[-1] / t.roof_per_1k_hh.iloc[0], 2)
    H[f"q5_q1_ratio_plug_{tag}"] = round(t.plug_per_1k_hh.iloc[-1] / t.plug_per_1k_hh.iloc[0], 2)

# ---- yearly additions, Land Bremen ----
yr = pd.DataFrame({"roof_units": roof.groupby(roof.date.dt.year).size(), "plug_units": plug.groupby(plug.date.dt.year).size(),
                   "roof_kw": roof.groupby(roof.date.dt.year).kw.sum()}).fillna(0)
yr.to_csv(OUT / "yearly.csv")
print(yr.tail(12).to_string())

# ---- validation: grid owner rate vs atlas owner rate per Ortsteil ----
json.dump(H, open(OUT / "headline.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(H, indent=1, ensure_ascii=False))
