"""Extract all solar units located in Land Bremen from the MaStR Gesamtdatenexport (XML, zipped).

Filter: Gemeindeschluessel 04011000 (Stadt Bremen) or 04012000 (Bremerhaven).
Also extracts the Katalogwerte table so codes can be decoded.
Output: work/mastr_solar_bremen.csv, work/mastr_katalog.csv
Source: Bundesnetzagentur, Marktstammdatenregister, dl-de/by-2-0.
"""
import zipfile, pathlib, sys, csv, time
from lxml import etree

ROOT = pathlib.Path(__file__).resolve().parents[1]
ZIP = ROOT / "raw" / sys.argv[1] if len(sys.argv) > 1 else ROOT / "raw" / "mastr_20261108.zip"
WORK = ROOT / "work"
GS = {"04011000", "04012000"}

zf = zipfile.ZipFile(ZIP)
names = zf.namelist()
print(len(names), "members; solar:", [n for n in names if n.startswith("EinheitenSolar")][:3], "...")

# Katalog
with zf.open("Katalogwerte.xml") as fh, open(WORK / "mastr_katalog.csv", "w", newline="") as out:
    w = csv.writer(out); w.writerow(["Id", "Wert", "KatalogKategorieId"])
    for _, el in etree.iterparse(fh, tag="Katalogwert"):
        w.writerow([el.findtext("Id"), el.findtext("Wert"), el.findtext("KatalogKategorieId")]); el.clear()
with zf.open("Katalogkategorien.xml") as fh, open(WORK / "mastr_katalogkategorien.csv", "w", newline="") as out:
    w = csv.writer(out); w.writerow(["Id", "Name"])
    for _, el in etree.iterparse(fh, tag="Katalogkategorie"):
        w.writerow([el.findtext("Id"), el.findtext("Name")]); el.clear()

rows, fields, total = [], set(), 0
t0 = time.time()
for n in sorted(n for n in names if n.startswith("EinheitenSolar")):
    with zf.open(n) as fh:
        for _, el in etree.iterparse(fh, tag="EinheitSolar"):
            total += 1
            gs = el.findtext("Gemeindeschluessel")
            if gs in GS:
                d = {c.tag: c.text for c in el}
                rows.append(d); fields.update(d)
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    print(n, "units scanned", total, "bremen", len(rows), f"{time.time()-t0:.0f}s", flush=True)

fields = sorted(fields)
with open(WORK / "mastr_solar_bremen.csv", "w", newline="") as out:
    w = csv.DictWriter(out, fieldnames=fields); w.writeheader(); w.writerows(rows)
print("DONE", total, len(rows))
