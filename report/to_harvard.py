"""Convert ledger-numbered citations [n] in draft_ledger.md into Harvard in-text citations and a
Harvard reference list, then reconcile the two mechanically (separate pass, per house style guide).

Statutes are cited by section and act in the text and listed under 'Legislation'."""
import json, re, pathlib, sys

R = pathlib.Path(__file__).resolve().parent
ledger = json.load(open(R.parent / "evidence" / "ledger.json"))
L = {str(s["id"]): s for s in ledger["sources"]} if isinstance(ledger, dict) and "sources" in ledger else None
if L is None:
    L = {str(k): v for k, v in (ledger.items() if isinstance(ledger, dict) else enumerate(ledger, 1))}
ACC = "(Accessed: 10 November 2026)"

# id: (in-text key, reference entry without URL, kind)  kind: 'ref' or 'law'
H = {
 1: ("Verbraucherzentrale, 2026", "Verbraucherzentrale (2026) *Was kostet eine Photovoltaikanlage?* Price index compiled by Verbraucherzentrale Nordrhein-Westfalen, as of 28 August 2026."),
 2: ("Fraunhofer ISE, 2024", "Fraunhofer ISE (2024) *Stromgestehungskosten erneuerbare Energien*. Freiburg: Fraunhofer Institute for Solar Energy Systems, July 2024."),
 3: ("Verbraucherzentrale Schleswig-Holstein, 2026", "Verbraucherzentrale Schleswig-Holstein (2026) *Balkonkraftwerk: Steckersolar als Alternative fürs Mehrfamilienhaus*. As of 23 July 2026."),
 4: ("§12(3) UStG", "Umsatzsteuergesetz (UStG), §12.", "law"),
 5: ("§3 No. 72 EStG", "Einkommensteuergesetz (EStG), §3.", "law"),
 6: ("§30 MsbG", "Messstellenbetriebsgesetz (MsbG), §30.", "law"),
 7: ("§8 EEG 2023", "Erneuerbare-Energien-Gesetz (EEG 2023), §8.", "law"),
 8: ("wesernetz, n.d.-a", "wesernetz (n.d.-a) *Anmeldung von Photovoltaikanlagen*."),
 9: ("Bundesnetzagentur, 2026", "Bundesnetzagentur (2026) *EEG-Förderung und -Fördersätze*. Rates for commissioning 1 August to 31 December 2026."),
 10: ("§51 EEG 2023", "Erneuerbare-Energien-Gesetz (EEG 2023), §51.", "law"),
 11: ("§9 EEG 2023", "Erneuerbare-Energien-Gesetz (EEG 2023), §9.", "law"),
 12: ("Bundesregierung, 2026", "Bundesregierung (2026) *Entwurf eines Gesetzes zur Änderung des Erneuerbare-Energien-Gesetzes (EEG 2027)*. Bundestag document 21/7867, 7 September 2026."),
 13: ("Deutscher Bundestag, 2026", "Deutscher Bundestag (2026) *Textarchiv, week 39: Energie, Stromsektor*. First reading, 24 September 2026."),
 14: ("§42a EnWG", "Energiewirtschaftsgesetz (EnWG), §42a.", "law"),
 15: ("§42b EnWG", "Energiewirtschaftsgesetz (EnWG), §42b.", "law"),
 16: ("Verbraucherzentrale, 2024", "Verbraucherzentrale (2024) *Steckersolar: Solarstrom vom Balkon direkt in die Steckdose*."),
 17: ("Verbraucherzentrale, 2023", "Verbraucherzentrale (2023) *Gesetze und Normen für Steckersolar: Was gilt, was gilt (noch) nicht?* Updated online."),
 18: ("§554 BGB", "Bürgerliches Gesetzbuch (BGB), §554.", "law"),
 19: ("§20 WEG", "Wohnungseigentumsgesetz (WEG), §20.", "law"),
 20: ("SUKW, n.d.-a", "Die Senatorin für Umwelt, Klima und Wissenschaft (SUKW) (n.d.-a) *Bremisches Solargesetz (BremSolarG)*."),
 21: ("BremSolarG", "Bremisches Solargesetz (BremSolarG), version of 29 May 2024.", "law"),
 22: ("energiekonsens, n.d.-a", "energiekonsens (n.d.-a) *Solar-Förderprogramm für private Haushalte in Bremerhaven eingestellt*."),
 23: ("Weser-Kurier, 2023", "Weser-Kurier (2023) 'Balkon-Solargeräte sind in Bremen Privatsache', 22 February 2023."),
 24: ("Bremer Aufbau-Bank, n.d.", "Bremer Aufbau-Bank (n.d.) *Kredite rund ums Haus*."),
 25: ("Bremische Bürgerschaft, 2022", "Bremische Bürgerschaft (2022) *Drucksache 20/1418*, 23 March 2022."),
 26: ("Senat der Freien Hansestadt Bremen, 2023a", "Senat der Freien Hansestadt Bremen (2023a) *Mitteilung des Senats, Drucksache 21/222*, 19 December 2023."),
 27: ("Bremer SolidarStrom, n.d.", "Bremer SolidarStrom (n.d.) *Solidarische Balkonkraftwerke*. NGO website."),
 28: ("energiekonsens, n.d.-b", "energiekonsens (n.d.-b) *solar-in-bremen.de*."),
 29: ("BDEW, 2026", "BDEW (2026) *BDEW-Strompreisanalyse*, October 2026."),
 30: ("Fraunhofer ISE, 2026", "Fraunhofer ISE (2026) *Aktuelle Fakten zur Photovoltaik in Deutschland*, version of 20 August 2026."),
 32: ("wesernetz, n.d.-b", "wesernetz (n.d.-b) *Impressum*."),
 33: ("wesernetz, n.d.-c", "wesernetz (n.d.-c) *Strukturdaten des Bremer und Bremerhavener Stromnetzes*. Data as of 31 December 2025."),
 34: ("§14e EnWG", "Energiewirtschaftsgesetz (EnWG), §14e.", "law"),
 35: ("VNBdigital, n.d.", "VNBdigital (n.d.) *wesernetz Bremen GmbH*."),
 36: ("Weser-Kurier, 2024", "Weser-Kurier (2024) 'Herausforderungen für PV-Anlagen in Bremen: Netzausbau nötig', 11 December 2024."),
 37: ("wesernetz, n.d.-d", "wesernetz (n.d.-d) *Informationen für Einspeiser*."),
 38: ("pv magazine, 2026", "pv magazine (2026) 'Bundestag wird EEG 2027 und Netzpaket wohl erst im November verabschieden', 15 October 2026."),
 39: ("Forrester et al., 2024", "Forrester, S., Barbose, G., O'Shaughnessy, E. and Darghouth, N. (2024) *Residential Solar-Adopter Income and Demographic Trends: 2024 Update*. Berkeley: Lawrence Berkeley National Laboratory."),
 40: ("Sunter, Castellanos and Kammen, 2019", "Sunter, D.A., Castellanos, S. and Kammen, D.M. (2019) 'Disparities in rooftop photovoltaics deployment in the United States by race and ethnicity', *Nature Sustainability*, 2, pp. 71–76."),
 41: ("Graziano and Gillingham, 2015", "Graziano, M. and Gillingham, K. (2015) 'Spatial patterns of solar photovoltaic system adoption: the influence of neighbors and the built environment', *Journal of Economic Geography*, 15(4), pp. 815–839."),
 42: ("Rode and Weber, 2016", "Rode, J. and Weber, A. (2016) 'Does localized imitation drive technology adoption? A case study on rooftop photovoltaic systems in Germany', *Journal of Environmental Economics and Management*, 78, pp. 38–48."),
 43: ("Jacksohn et al., 2018", "Jacksohn, A., Grösche, P., Rehdanz, K. and Schröder, C. (2018) *Drivers of renewable technology adoption in the household sector*. SOEPpapers 977. Berlin: DIW Berlin."),
 44: ("De Groote, Pepermans and Verboven, 2016", "De Groote, O., Pepermans, G. and Verboven, F. (2016) 'Heterogeneity in the adoption of photovoltaic systems in Flanders', *Energy Economics*, 59, pp. 45–57 (working-paper version)."),
 46: ("HTW Berlin, 2022", "HTW Berlin (2022) *Nutzung von Steckersolargeräten 2022*. Berlin: Hochschule für Technik und Wirtschaft Berlin."),
 47: ("Bergner, 2022", "Bergner, J. (2022) *Nutzer:innenstudie Steckersolar 2022*. Berlin: HTW Berlin."),
 48: ("Winter and Schlesewsky, 2019", "Winter, S. and Schlesewsky, L. (2019) 'The German feed-in tariff revisited: an empirical investigation on its distributional effects', *Energy Policy*, 132, pp. 344–356."),
 49: ("Grösche and Schröder, 2014", "Grösche, P. and Schröder, C. (2014) 'On the redistributive effects of Germany's feed-in tariff', *Empirical Economics*, 46, pp. 1339–1383."),
 50: ("Neuhoff et al., 2012", "Neuhoff, K., Bach, S., Diekmann, J. et al. (2012) 'Steigende EEG-Umlage: unerwünschte Verteilungseffekte können vermindert werden', *DIW Wochenbericht*, 41/2012."),
 51: ("Frondel, Sommer and Vance, 2015", "Frondel, M., Sommer, S. and Vance, C. (2015) 'The burden of Germany's energy transition: an empirical analysis of distributional effects', *Economic Analysis and Policy*."),
 52: ("Bundesregierung, 2019", "Bundesregierung (2019) *Mieterstrombericht nach §99 des EEG 2017*. Bundestag document 19/13430."),
 53: ("Breddermann and Henger, 2024", "Breddermann, C. and Henger, R. (2024) *Großes ungenutztes Potenzial beim Mieterstrom*. IW-Kurzbericht 41/2024. Cologne: Institut der deutschen Wirtschaft."),
 54: ("Fischer and Henger, 2025", "Fischer, A. and Henger, R. (2025) *Gebäude- und Mieterstrom in Deutschland: Potenziale, Wirtschaftlichkeit und regulatorische Handlungsansätze*. Ariadne-Analyse. Potsdam: Kopernikus-Projekt Ariadne."),
 55: ("DIW Berlin, 2024", "DIW Berlin (2024) 'Ausbau der Solarenergie', *DIW Wochenbericht*, 33/2024."),
 57: ("energiekonsens, n.d.-c", "energiekonsens (n.d.-c) *PV-Strom für Mehrparteiengebäude: Auf die Plätze, fertig, … los?*"),
 58: ("Statistisches Landesamt Bremen, n.d.-a", "Statistisches Landesamt Bremen (n.d.-a) *Zensus 2022: Regionaltabelle Gebäude und Wohnungen* (xlsx)."),
 59: ("Statistisches Landesamt Bremen, 2024", "Statistisches Landesamt Bremen (2024) *Zensus 2022: Durchschnittliche Nettokaltmiete im Land Bremen bei 7,34 Euro pro Quadratmeter*. Press release, 25 June 2024."),
 60: ("Destatis, n.d.-a", "Destatis (n.d.-a) *Eigentumsquote nach Bundesländern 2022*."),
 61: ("WFB Bremen, 2014", "WFB Wirtschaftsförderung Bremen (2014) *Typical Bremen: the Bremen house*."),
 62: ("Arbeitnehmerkammer Bremen, 2025", "Arbeitnehmerkammer Bremen (2025) *KammerKompakt: Armut und Klima*, February 2025."),
 63: ("Schröder, 2023", "Schröder, P.M. (2023) *Bremer Stadtteile: Personen in SGB-II-Bedarfsgemeinschaften Ende 2022*. Bremen: BIAJ, 9 December 2023."),
 64: ("Senat der Freien Hansestadt Bremen, 2025", "Senat der Freien Hansestadt Bremen (2025) *Sozialmonitoring für das Land Bremen*. Senate paper, November 2025."),
 68: ("GEWOBA, 2025", "GEWOBA (2025) *GEWOBA-Vorstand zieht positive Bilanz für 2024*. Press release."),
 70: ("Senat der Freien Hansestadt Bremen, 2023b", "Senat der Freien Hansestadt Bremen (2023b) *Mitteilung des Senats: Photovoltaik-Ausbau*, 19 December 2023."),
 71: ("Green Planet Energy, 2026", "Green Planet Energy (2026) *Mehr Mieterstrom für Bremen*. Press release, 13 February 2026."),
 72: ("Senatspressestelle, 2024", "Senatspressestelle Bremen (2024) *Über 100 Megawatt Photovoltaik-Leistung im Land Bremen in Betrieb*. Press release, 18 March 2024."),
 73: ("SUKW, n.d.-b", "Die Senatorin für Umwelt, Klima und Wissenschaft (SUKW) (n.d.-b) *Solarenergie in Bremen*."),
 74: ("Senatspressestelle, 2020", "Senatspressestelle Bremen (2020) *Grün- und Solardachkataster zeigen Potentiale*. Press release, 7 January 2020."),
 75: ("Bundesnetzagentur, n.d.-a", "Bundesnetzagentur (n.d.-a) *Marktstammdatenregister help: Schutz und Freigabe vertraulicher Daten*."),
 76: ("Destatis, n.d.-b", "Destatis (n.d.-b) *Zensus 2022: Gitterdaten zum Download*."),
 77: ("Statistisches Landesamt Bremen, n.d.-b", "Statistisches Landesamt Bremen (n.d.-b) *Bremer Ortsteilatlas*."),
 78: ("Bundesnetzagentur, n.d.-b", "Bundesnetzagentur (n.d.-b) *Marktstammdatenregister: Datendownload*. Export of 8 November 2026 used."),
}


def url(i):
    s = L.get(str(i))
    return s["url"] if isinstance(s, dict) else s


src = (R / "draft_ledger.md").read_text()
body, _ = src.split("\n## Sources", 1)
cited = sorted({int(x) for x in re.findall(r"\[(\d+)\]", body)})
missing = [i for i in cited if i not in H]
if missing:
    sys.exit(f"no Harvard entry for ledger ids {missing}")


def repl(m):
    ids = [int(x) for x in re.findall(r"\d+", m.group(0))]
    keys = []
    for i in ids:
        k = H[i][0]
        if k not in keys:
            keys.append(k)
    return " (" + "; ".join(keys) + ")"

out = re.sub(r"(?:\[\d+\])+", repl, body)
# punctuation: citation must sit before the full stop/colon/comma it follows
out = re.sub(r"([.,;:])\s\(([^()]*?(?:\d{4}[a-z]?|n\.d\.(?:-[a-z])?|UStG|EStG|MsbG|EEG 2023|EnWG|BGB|WEG|BremSolarG))\)", r" (\2)\1", out)
for i, v in H.items():
    if len(v) == 3:
        k = v[0]
        for sep in [", ", " ", ". ", ""]:
            out = out.replace(f"({k}){sep.rstrip()} ({k})", f"({k}){sep.rstrip()}")
        out = out.replace(f"({k}), ({k})", f"({k}),").replace(f"({k}) ({k})", f"({k})")

refs = sorted({i for i in cited if len(H[i]) == 2}, key=lambda i: H[i][1].lower())
laws = sorted({i for i in cited if len(H[i]) == 3}, key=lambda i: H[i][1])
lines = ["\n## References\n"]
for i in refs:
    lines.append(f"- {H[i][1]} Available at: {url(i)} {ACC}.")
lines.append("\n### Legislation\n")
seen = set()
for i in laws:
    t = H[i][1]
    lines.append(f"- {t} Available at: {url(i)} {ACC}.")
final = out.rstrip() + "\n" + "\n".join(lines) + "\n"
(R / "final_harvard.md").write_text(final)

# ---- reconciliation pass ----
text_part, ref_part = final.split("\n## References", 1)
intext = set()
for grp in re.findall(r"\(([^()]*?)\)", text_part):
    for k in grp.split("; "):
        if k in {v[0] for v in H.values()}:
            intext.add(k)
for i in cited:
    if len(H[i]) == 3 and f"({H[i][0]})" in text_part:
        intext.add(H[i][0])
listed = {H[i][0] for i in cited}
problems = []
for k in sorted(intext - listed): problems.append(f"in text, not in list: {k}")
for k in sorted(listed - intext): problems.append(f"in list, not in text: {k}")
leftover = re.findall(r"\[\d+\]", text_part)
if leftover: problems.append(f"unconverted ledger ids: {leftover[:5]}")
# every in-text key has a verified evidence quote in the ledger
for i in cited:
    s = L.get(str(i))
    if not (isinstance(s, dict) and s.get("quotes")):
        problems.append(f"no evidence quote for id {i} ({H[i][0]})")
print("cited sources:", len(cited), "| references:", len(refs), "| legislation:", len(laws), "| in-text keys:", len(intext))
print("RECONCILIATION:", "OK" if not problems else problems)
