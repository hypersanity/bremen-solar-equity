"""Illustrative household economics (simple payback, no discounting). Inputs are cited in the report;
yield and self-consumption assumptions are marked as assumptions there."""
import json, itertools, pathlib
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
P_GRID = 0.373      # €/kWh, BDEW 2026 average household price
FIT = 0.0770        # €/kWh, EEG partial feed-in <=10 kW, commissioning Aug–Dec 2026
res = {}
# rooftop 8 kWp, VZ price band >6–8 kWp = 1,820 €/kWp
capex = 8 * 1820
for name, y, sc, fit in [("base: 900 kWh/kWp, 30% SC, FIT", 900, 0.30, FIT), ("40% SC, FIT", 900, 0.40, FIT),
                         ("30% SC, feed-in worth 0 (no FIT)", 900, 0.30, 0.0), ("lower yield 800, 30% SC, FIT", 800, 0.30, FIT),
                         ("price 30 ct, 30% SC, FIT", 900, 0.30, FIT)]:
    p = 0.30 if name.startswith("price 30") else P_GRID
    gen = 8 * y; save = gen * sc * p; feed = gen * (1 - sc) * fit
    res["roof_" + name] = dict(capex=capex, gen_kwh=gen, saving_eur=round(save, 0), feedin_eur=round(feed, 0),
                               annual_eur=round(save + feed, 0), payback_yr=round(capex / (save + feed), 1))
res["capex_share_of_median_income_28237"] = round(capex / 16500, 2)
res["capex_share_of_median_income_28355"] = round(capex / 44300, 2)
# plug-in 0.8 kWp (800 W inverter), price 200–600 €
rows = []
for y, sc, price in itertools.product([500, 700], [0.4, 0.7], [400, 600]):
    ann = 0.8 * y * sc * P_GRID
    rows.append(dict(yield_kwh_per_kwp=y, self_consumption=sc, price=price, annual_eur=round(ann, 0), payback_yr=round(price / ann, 1)))
res["plug_grid"] = rows
json.dump(res, open(OUT / "economics.json", "w"), indent=1)
print(json.dumps(res, indent=1))
