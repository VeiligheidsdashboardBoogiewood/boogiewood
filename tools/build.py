"""Bouwt de web-app opnieuw: rekent het dashboard door, haalt namen eruit en versleutelt de data.

Gebruik (vanuit de hoofdmap van de repository):
  python3 tools/build.py --code "<toegangscode>" --beheer "<beheersleutel>" [--dir map_met_datasets] [--set id=bestand.json ...]

- Zonder --dir/--set worden de ruwe datasets uit data/raw.enc.json gebruikt.
- --dir: map met <id>.json of boogiewood_<id>.json; die vervangen de bestaande datasets.
- --set id=pad: één dataset vervangen (bijv. --set wind_knmi=/tmp/wind.json).
--peildatum zet de peildatum op vandaag (alleen bij de dagelijkse update met verse Capptions/Bouwpas-data).
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))
from crypt import encrypt, decrypt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

# Namen -> rol. Geen persoonsnamen in de app.
NAMEN = [
    (r"\s*\(Ciske / Ate van Geest\)", ""), (r"Ciske / Ate van Geest", "Hamlet"), (r"Ate van Geest", "Hamlet"), (r"\bCiske\b", "Hamlet"),
    (r"Onno van ['’]t [Ww]out", "QHSE"),
    (r"Joey Twigt", "Projectveiligheidskundige"), (r"Maikel Meeuwissen", "Projectleider realisatie"),
    (r"Jason Daum", "Uitvoerder (plv. Hoofd BHV)"), (r"Jeroen Traa", "Uitvoerder"), (r"Koen van Heugten", "Bouwplaatscoördinator"),
    (r"Bas Timmers", "Coördinator omgevingsveiligheid"), (r"Martijn Otterspeer", "Projectleider voorbereiding"),
    (r"Anne Ippel", "Projectmanager realisatie"),
    # losse voornamen in vrije tekst
    (r"\bKoen\b", "bouwplaatscoördinator"), (r"\bJason\b", "uitvoerder"), (r"\bJeroen\b", "uitvoerder"),
    (r"\bMaikel\b", "projectleider"), (r"\bBas\b", "coördinator omgevingsveiligheid"), (r"\bJoey\b", "projectveiligheidskundige"),
    (r"\bMartijn\b", "projectleider voorbereiding"), (r"\bAnne\b", "projectmanager"), (r"\bOnno\b", "QHSE"),
]
WEG = {"personeel", "verbeteracties"}
NAAMVELDEN = {"naam"}


def schoon(x):
    if isinstance(x, str):
        for p, r in NAMEN:
            x = re.sub(p, r, x)
        return x
    if isinstance(x, list):
        return [schoon(v) for v in x]
    if isinstance(x, dict):
        return {k: ("" if k in NAAMVELDEN and isinstance(v, str) else schoon(v)) for k, v in x.items()}
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True, help="toegangscode voor collega's (app-data)")
    ap.add_argument("--beheer", required=True, help="beheersleutel voor de ruwe data (niet delen)")
    ap.add_argument("--dir")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--zonder-namen", action="store_true", help="namen vervangen door rollen")
    ap.add_argument("--peildatum", action="store_true", help="peildatum (Status per) op vandaag zetten; alleen bij de dagelijkse update")
    ap.add_argument("--stand", help="tekst voor de stand, standaard nu")
    a = ap.parse_args()

    raw = decrypt(json.load(open(P("data", "raw.enc.json"))), a.beheer) if os.path.exists(P("data", "raw.enc.json")) else {}
    if a.dir:
        for f in glob.glob(os.path.join(a.dir, "*.json")):
            k = os.path.basename(f)[:-5].replace("boogiewood_", "")
            raw[k] = json.load(open(f))
    for s in a.set:
        k, f = s.split("=", 1)
        raw[k] = json.load(open(f))
    nu = datetime.now(ZoneInfo("Europe/Amsterdam"))
    if a.peildatum:
        raw["project"][0]["peildatum"] = nu.strftime("%Y-%m-%d")

    # zzp'ers zijn herleidbaar tot één persoon: in de app samen als groep
    calc_raw = json.loads(json.dumps(raw))
    for r in (calc_raw.get("bp_vca", []) if a.zonder_namen else []):
        if r.get("zzp") == "Ja":
            r["werkgever"] = "Zzp'ers"
    with tempfile.TemporaryDirectory() as t:
        json.dump(calc_raw, open(os.path.join(t, "raw.json"), "w"), ensure_ascii=False)
        subprocess.run(["node", P("tools", "calc.js"), P("src", "dashboard.html"), os.path.join(t, "raw.json"), os.path.join(t, "R.json")], check=True)
        R = json.load(open(os.path.join(t, "R.json")))

    page = open(P("src", "dashboard.html")).read()
    buiten = re.sub(r"dash\.calc\(\s*['\"][\w-]+['\"]", "", page)
    R = {k: v for k, v in R.items() if k not in WEG and re.search(r"""(['"`])%s\1""" % re.escape(k), buiten)}
    if a.zonder_namen:
        R = schoon(R)
    # controle: geen bekende namen meer (alleen bij --zonder-namen)
    tekst = json.dumps(R, ensure_ascii=False)
    namen = set()
    for ds in ("organisatie", "personeel"):
        for r in raw.get(ds, []):
            if r.get("naam"): namen.add(r["naam"])
    for ds, veld in (("inspecties", "door"), ("inspecties", "gecontroleerd_door"), ("meldingen", "door"), ("toolboxen", "gegeven_door")):
        for r in raw.get(ds, []):
            if r.get(veld): namen.add(r[veld])
    over = sorted(n for n in namen if n and n in tekst) if a.zonder_namen else []
    if over:
        sys.exit("Namen gevonden in app-data: " + ", ".join(over))

    # wind.json alleen vervangen als deze meting nieuwer is (GitHub Actions schrijft hem elk uur)
    try:
        oud = json.load(open(P("data", "wind.json")))[0]["tijd_utc"]
    except Exception:
        oud = ""
    if raw["wind_knmi"][0]["tijd_utc"] > oud:
        json.dump(raw["wind_knmi"], open(P("data", "wind.json"), "w"))
    json.dump(encrypt(R, a.code, {"updated": nu.isoformat(timespec="minutes")}), open(P("data", "app.enc.json"), "w"))
    json.dump(encrypt(raw, a.beheer, {"updated": nu.isoformat(timespec="minutes")}), open(P("data", "raw.enc.json"), "w"))
    maak_index(page, a.zonder_namen)
    print("klaar", nu.isoformat(timespec="minutes"), len(R), "datasets")


def maak_index(page, zonder_namen):
    shell = open(P("tools", "shell.html")).read()
    dash = page.replace('<link rel="stylesheet" href="dashboard.css">', "<style>" + open(P("src", "dashboard.css")).read() + "</style>")
    dash = dash.replace('<link rel="stylesheet" href="hero.css">', "<style>" + open(P("src", "hero.css")).read() + "</style>")
    if zonder_namen:
        dash = dash.replace('<th data-field="naam">Naam</th>', "")
        dash = dash.replace("org: [{ k: 'naam' }, { k: 'rol', wrap: true }", "org: [{ k: 'rol', wrap: true }")
    open(P("index.html"), "w").write(shell.replace("{{DASH}}", dash))


if __name__ == "__main__":
    main()
