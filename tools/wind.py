"""Haalt de laatste KNMI-meting van station Voorschoten op en schrijft data/wind.json.
Draait elk uur via GitHub Actions (.github/workflows/wind.yml)."""
import html, json, re, sys, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

URL = "https://www.knmi.nl/nederland-nu/weer/waarnemingen"
MAANDEN = {m: i for i, m in enumerate(["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"], 1)}

def tekst(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def main(uit):
    req = urllib.request.Request(URL + "?v=" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M"), headers={"User-Agent": "Mozilla/5.0 (veiligheidsdashboard)"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    m = re.search(r"Waarnemingen\s+(\d{1,2})\s+([a-z]+)\s+(\d{4})\s+(\d{1,2}):(\d{2})\s+uur", tekst(page))
    if not m:
        sys.exit("tijd niet gevonden")
    d, mnd, j, u, mi = m.groups()
    lokaal = datetime(int(j), MAANDEN[mnd], int(d), int(u), int(mi), tzinfo=ZoneInfo("Europe/Amsterdam"))
    rijen = [[tekst(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)] for r in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)]
    kop = next((r for r in rijen if r and r[0].lower().startswith("station")), None)
    rij = next((r for r in rijen if r and r[0] == "Voorschoten"), None)
    if not kop or not rij:
        sys.exit("tabel of Voorschoten niet gevonden")
    k = {re.sub(r"\s+", " ", c).lower(): i for i, c in enumerate(kop)}
    def kol(naam):
        i = next(i for c, i in k.items() if c.startswith(naam))
        return rij[i]
    richting, bft = kol("wind (bft)").split()
    out = [{
        "station": "Voorschoten", "stationnummer": 215,
        "tijd_utc": lokaal.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z"),
        "richting": richting, "wind_10m_ms": float(kol("wind (m/s)").replace(",", ".")),
        "bft_10m": int(bft), "stoot_10m_kmh": float(kol("windstoot").replace(",", ".")),
    }]
    if out[0]["stoot_10m_kmh"].is_integer():
        out[0]["stoot_10m_kmh"] = int(out[0]["stoot_10m_kmh"])
    json.dump(out, open(uit, "w"))
    print(out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/wind.json")
