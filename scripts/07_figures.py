"""Figures for the Bremen solar-equity study (static PNG, report-ready) + spatial autocorrelation."""
import pathlib, json
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
W = ROOT / "work"; OUT = ROOT / "out"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})

m = pd.read_csv(OUT / "plz_metrics.csv", dtype={"plz": str}).set_index("plz")
plz = gpd.read_file(W / "plz_bremen.gpkg").set_index("postal_code")[["geometry"]].join(m, how="inner")
land = gpd.read_file(W / "osm_land_bremen.geojson").to_crs(25832)
st = gpd.read_file(W / "osm_admin10.geojson").to_crs(25832)
ot = gpd.read_file(W / "ortsteile_atlas.gpkg").to_crs(25832)

BREAKS = [0, 10, 20, 30, 45, 70, 120]
COLS = ["#fff7bc", "#fee391", "#fec44f", "#fe9929", "#d95f0e", "#8c2d04"]
cmap = ListedColormap(COLS); norm = BoundaryNorm(BREAKS, cmap.N)
LABELS = ["< 10", "10 – 20", "20 – 30", "30 – 45", "45 – 70", "≥ 70"]

hb = plz[~plz.index.str.startswith("275")]; bhv = plz[plz.index.str.startswith("275")]


def panel(ax, gdf, col, title, fs=9):
    gdf.plot(column=col, cmap=cmap, norm=norm, ax=ax, edgecolor="white", linewidth=0.8)
    for _, r in gdf.iterrows():
        p = r.geometry.representative_point()
        ax.annotate(f"{r[col]:.0f}", (p.x, p.y), ha="center", va="center", fontsize=fs if r.geometry.area > 3e6 else fs - 1.5,
                    color="black" if r[col] < 45 else "white", fontweight="bold")
    x0, y0, x1, y1 = gdf.total_bounds; pad = 600
    ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad)
    ax.set_title(title, fontsize=12.5, loc="left"); ax.set_axis_off()


def choropleth(col, title, fname, subtitle):
    fig = plt.figure(figsize=(18, 10.5))
    ax1 = fig.add_axes([0.0, 0.07, 0.70, 0.85])
    panel(ax1, hb, col, "Stadt Bremen")
    stb = gpd.clip(st, hb.union_all().buffer(1)); stb.boundary.plot(ax=ax1, color="#444", linewidth=0.5, linestyle=":")
    ax1.set_xlim(*ax1.get_xlim()); ax1.set_ylim(*ax1.get_ylim())
    ax2 = fig.add_axes([0.71, 0.40, 0.28, 0.50]); ax2.set_facecolor("none")
    panel(ax2, bhv, col, "Bremerhaven (~50 km north; same classes)", fs=9)
    for ax in (ax1, ax2):
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        L = 2000; ax.plot([x0 + 0.04 * (x1 - x0), x0 + 0.04 * (x1 - x0) + L], [y0 + 0.03 * (y1 - y0)] * 2, color="k", lw=3)
        ax.text(x0 + 0.04 * (x1 - x0) + L / 2, y0 + 0.05 * (y1 - y0), "2 km", ha="center", fontsize=9)
        ax.annotate("N", xy=(x1 - 0.05 * (x1 - x0), y1 - 0.05 * (y1 - y0)), xytext=(x1 - 0.05 * (x1 - x0), y1 - 0.13 * (y1 - y0)),
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.5), ha="center", fontsize=11, fontweight="bold")
    handles = [Patch(facecolor=c, edgecolor="#999", label=l) for c, l in zip(COLS, LABELS)]
    fig.legend(handles=handles, title=title, loc="lower left", bbox_to_anchor=(0.74, 0.08), fontsize=12, title_fontsize=12.5, frameon=True)
    fig.text(0.01, 0.965, subtitle, fontsize=15, fontweight="bold")
    fig.text(0.01, 0.015, "Labels: value per postcode (PLZ codes: see key map, Fig. 0). Units in operation per MaStR Gesamtdatenexport 2026-11-08 (BNetzA, dl-de/by-2-0); "
             "households: Zensus 2022 100 m grid (Destatis);\nPLZ polygons © OpenStreetMap contributors, ODbL (openstreetmap.org/copyright), clipped to Land Bremen. Dotted lines: Stadtteil boundaries (OSM).",
             fontsize=8.5, color="#333")
    fig.savefig(FIG / fname, dpi=170); plt.close(fig)


choropleth("roof_per_1k_hh", "Rooftop PV units\nper 1,000 households", "fig1_map_rooftop_per_1000hh.png",
           "Residential rooftop PV ('Haushalt' building units) per 1,000 households, by postcode")
choropleth("plug_per_1k_hh", "Plug-in PV units\nper 1,000 households", "fig2_map_plugin_per_1000hh.png",
           "Plug-in ('balcony') PV units per 1,000 households, by postcode")

# ---- key map: PLZ codes + Stadtteil names ----
fig = plt.figure(figsize=(18, 10.5)); ax1 = fig.add_axes([0.0, 0.03, 0.70, 0.9])
hb.plot(ax=ax1, color="#eef2f5", edgecolor="#555", linewidth=0.8)
gpd.clip(st, hb.union_all().buffer(1)).boundary.plot(ax=ax1, color="#c0392b", linewidth=1.0)
for i, r in hb.iterrows():
    p = r.geometry.representative_point(); ax1.annotate(i, (p.x, p.y), ha="center", va="center", fontsize=9 if r.geometry.area > 3e6 else 7.5, fontweight="bold")
stc = gpd.clip(st, hb.union_all().buffer(1))
for _, r in stc.iterrows():
    if r.geometry.area > 2.5e6:
        p = r.geometry.representative_point(); ax1.annotate(r["name"], (p.x, p.y - 650), ha="center", fontsize=8.5, color="#c0392b", style="italic")
x0, y0, x1, y1 = hb.total_bounds; ax1.set_xlim(x0 - 600, x1 + 600); ax1.set_ylim(y0 - 600, y1 + 600); ax1.set_axis_off()
ax2 = fig.add_axes([0.71, 0.30, 0.28, 0.55]); bhv.plot(ax=ax2, color="#eef2f5", edgecolor="#555", linewidth=0.8)
for i, r in bhv.iterrows():
    p = r.geometry.representative_point(); ax2.annotate(i, (p.x, p.y), ha="center", va="center", fontsize=9, fontweight="bold")
ax2.set_title("Bremerhaven", loc="left"); ax2.set_axis_off()
fig.text(0.01, 0.965, "Key map: postcodes (black) and Stadtteile (red italic), Land Bremen", fontsize=15, fontweight="bold")
fig.text(0.01, 0.012, "Boundaries © OpenStreetMap contributors, ODbL (openstreetmap.org/copyright), clipped to Land Bremen.", fontsize=9, color="#333")
fig.savefig(FIG / "fig0_key_map_plz.png", dpi=150); plt.close(fig)

# ---- explanatory small multiples (Stadt Bremen + Bremerhaven side panels) ----
fig, axes = plt.subplots(1, 3, figsize=(17, 7.4))
specs = [("owner_rate_pct", "Owner-occupancy rate (%)", "Greens"), ("share_dw_1_2_family_pct", "Dwellings in 1–2-family houses (%)", "Blues"),
         ("median_income_eur", "Median taxable income per taxpayer\n(k€, 2020; Ortsteile, Stadt Bremen only)", "Purples")]
for ax, (col, t, cm) in zip(axes, specs):
    if col == "median_income_eur":
        o = ot.dropna(subset=[col])
        o.plot(column=col, cmap=cm, ax=ax, legend=True, edgecolor="white", linewidth=0.4, scheme="quantiles", k=5,
               legend_kwds={"loc": "upper left", "bbox_to_anchor": (0.0, 0.02), "ncols": 3, "fontsize": 9.5, "title": "quintiles (Ortsteile)", "fmt": "{:.1f}"})
        ot[ot[col].isna()].plot(ax=ax, color="#ddd", edgecolor="white", linewidth=0.4)
    else:
        hb.plot(column=col, cmap=cm, ax=ax, legend=True, edgecolor="white", linewidth=0.5, scheme="quantiles", k=5,
                legend_kwds={"loc": "upper left", "bbox_to_anchor": (0.0, 0.02), "ncols": 3, "fontsize": 9.5, "title": "quintiles (PLZ)", "fmt": "{:.0f}"})
    ax.set_title(t, fontsize=11.5, loc="left"); ax.set_axis_off()
fig.suptitle("Context variables, Stadt Bremen (Zensus 2022 grid aggregated to PLZ; income from Bremer Ortsteilatlas)", fontsize=13, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.text(0.01, 0.01, "Data: Zensus 2022 (Destatis, dl-de/by-2-0); Bremer Ortsteilatlas (Statistisches Landesamt Bremen, CC BY); own calculation and presentation. "
         "Postcode boundaries © OpenStreetMap contributors, ODbL (openstreetmap.org/copyright).", fontsize=9, color="#333")
fig.savefig(FIG / "fig3_context_maps.png", dpi=150); plt.close(fig)

# ---- scatter ----
fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=False)
for ax, (y, t) in zip(axes, [("roof_per_1k_hh", "Rooftop PV per 1,000 households"), ("plug_per_1k_hh", "Plug-in PV per 1,000 households")]):
    a = m[m.city == "Bremen"]; b = m[m.city == "Bremerhaven"]
    sc = ax.scatter(a.share_dw_1_2_family_pct, a[y], c=a.median_income_keur_ot_weighted, cmap="viridis", s=60, edgecolor="k", linewidth=0.4, label="Stadt Bremen (colour = median income)")
    ax.scatter(b.share_dw_1_2_family_pct, b[y], marker="^", facecolor="none", edgecolor="crimson", s=70, label="Bremerhaven (no income data)")
    for i, r in m.iterrows():
        if r[y] > m[y].quantile(0.85) or r[y] < m[y].quantile(0.1):
            ax.annotate(i, (r.share_dw_1_2_family_pct, r[y]), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Dwellings in 1–2-family houses (%) — Zensus 2022"); ax.set_ylabel(t); ax.set_title(t, loc="left")
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5, loc="upper left")
cb = fig.colorbar(sc, ax=axes, shrink=0.8); cb.set_label("Median taxable income, k€ (2020)")
fig.savefig(FIG / "fig4_scatter_housing_type.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---- Lorenz / concentration curves ----
cur = json.load(open(OUT / "curves.json")); H = json.load(open(OUT / "headline.json"))
fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
ax = axes[0]
ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="equal distribution")
for k, lab_, c in [("lorenz_roof_per_1k_hh", f"Rooftop (Gini {H['gini_roof_per_1k_hh']:.2f})", "#d95f0e"), ("lorenz_plug_per_1k_hh", f"Plug-in (Gini {H['gini_plug_per_1k_hh']:.2f})", "#2c7fb8")]:
    ax.plot(*cur[k], color=c, lw=2, label=lab_)
ax.set_title("Lorenz curves across households (40 PLZ)", loc="left"); ax.set_xlabel("Cumulative share of households (PLZ ranked by PV rate)"); ax.set_ylabel("Cumulative share of PV units"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
ax = axes[1]
ax.plot([0, 1], [0, 1], "k--", lw=0.8)
for k, lab_, c, ls in [("conc_income_roof_per_1k_hh", f"Rooftop, ranked by income (CI {H['CI_income_roof_per_1k_hh']:.2f})", "#d95f0e", "-"),
                       ("conc_income_plug_per_1k_hh", f"Plug-in, ranked by income (CI {H['CI_income_plug_per_1k_hh']:.2f})", "#2c7fb8", "-"),
                       ("conc_owner_roof_per_1k_hh", f"Rooftop, ranked by owner rate (CI {H['CI_owner_roof_per_1k_hh']:.2f})", "#d95f0e", ":"),
                       ("conc_owner_plug_per_1k_hh", f"Plug-in, ranked by owner rate (CI {H['CI_owner_plug_per_1k_hh']:.2f})", "#2c7fb8", ":")]:
    ax.plot(*cur[k], color=c, lw=2, ls=ls, label=lab_)
ax.set_title("Concentration curves (poorest / most-renting PLZ first)", loc="left"); ax.set_xlabel("Cumulative share of households"); ax.set_ylabel("Cumulative share of PV units"); ax.legend(fontsize=8.5); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "fig5_lorenz_concentration.png", dpi=150); plt.close(fig)

# ---- yearly ----
yr = pd.read_csv(OUT / "yearly.csv", index_col=0); yr = yr[yr.index >= 2010]
fig, ax = plt.subplots(figsize=(10, 4.6))
x = yr.index.astype(int); wdt = 0.4
ax.bar(x - wdt / 2, yr.roof_units, wdt, label="Rooftop ('Haushalt')", color="#d95f0e")
ax.bar(x + wdt / 2, yr.plug_units, wdt, label="Plug-in", color="#2c7fb8")
ax.set_title("New residential PV units by commissioning year, Land Bremen (units still in operation)", loc="left", fontsize=11.5)
ax.set_ylabel("Units"); ax.legend(); ax.grid(axis="y", alpha=0.3); ax.set_xticks(x); ax.tick_params(axis="x", rotation=45)
ax.annotate("2026 = 1 Jan – 8 Nov\n(+ registration lag)", (2026, yr.loc[2026, "plug_units"]), xytext=(2019.3, 2300), fontsize=9, arrowprops=dict(arrowstyle="->"))
fig.tight_layout(); fig.savefig(FIG / "fig6_yearly_additions.png", dpi=150); plt.close(fig)

# ---- Moran's I (queen contiguity, Stadt Bremen PLZ) ----
def morans(gdf, col, perms=9999, seed=1):
    g = gdf.reset_index(drop=True); n = len(g)
    Wm = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            if g.geometry[i].buffer(1).intersects(g.geometry[j]):
                Wm[i, j] = Wm[j, i] = 1
    rs = Wm.sum(1, keepdims=True); Wr = np.divide(Wm, rs, out=np.zeros_like(Wm), where=rs > 0)
    x = g[col].values; z_ = x - x.mean()
    I = n / Wr.sum() * (z_ @ Wr @ z_) / (z_ @ z_)
    rng = np.random.default_rng(seed); sims = np.empty(perms)
    for k in range(perms):
        zp = rng.permutation(z_); sims[k] = n / Wr.sum() * (zp @ Wr @ zp) / (zp @ zp)
    p = (np.sum(sims >= I) + 1) / (perms + 1)
    return round(float(I), 3), round(float(p), 4), int(Wm.sum() / 2)

import statsmodels.api as sm
res = {}
for col in ["roof_per_1k_hh", "plug_per_1k_hh"]:
    res[col] = morans(hb, col)
s = hb.dropna(subset=["median_income_keur_ot_weighted"]).copy()
X = sm.add_constant(s[["share_dw_1_2_family_pct", "median_income_keur_ot_weighted"]]); s["resid"] = sm.OLS(s.roof_per_1k_hh, X).fit().resid
res["ols_resid_roof"] = morans(s, "resid")
json.dump(res, open(OUT / "morans.json", "w"), indent=1)
print("Moran's I (I, p, links):", res)
