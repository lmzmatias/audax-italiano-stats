"""
Prueba fixtures de Audax Italiano (ID 2329) en api-sports.io
"""
import json
import argparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE_URL = "https://v3.football.api-sports.io"
AUDAX_ID = 2329


def get(api_key, path):
    url = BASE_URL + path
    req = Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
            errors = data.get("errors", {})
            if errors:
                print("  API errors:", errors)
            return data
    except HTTPError as e:
        print("  HTTPError:", e.code, e.reason, e.read().decode()[:200])
        return None
    except URLError as e:
        print("  URLError:", e)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()
    key = args.api_key

    # Partido en vivo
    print("=== Partido en vivo ===")
    data = get(key, f"/fixtures?team={AUDAX_ID}&live=all")
    if data:
        fixtures = data.get("response", [])
        print(f"  En vivo: {len(fixtures)}")
        for f in fixtures:
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            status = f.get("fixture", {}).get("status", {})
            elapsed = status.get("elapsed")
            print(f"  {teams.get('home',{}).get('name')} {goals.get('home')}-{goals.get('away')} {teams.get('away',{}).get('name')} | {status.get('long')} {elapsed}'")

    # Ultimos 10 partidos
    print("\n=== Ultimos 10 partidos (temporada 2026) ===")
    data2 = get(key, f"/fixtures?team={AUDAX_ID}&season=2026&last=10")
    if data2:
        fixtures = data2.get("response", [])
        print(f"  Partidos: {len(fixtures)}")
        for f in fixtures:
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            date = f.get("fixture", {}).get("date", "")[:10]
            status = f.get("fixture", {}).get("status", {}).get("short")
            home = teams.get("home", {}).get("name")
            away = teams.get("away", {}).get("name")
            gh = goals.get("home")
            ga = goals.get("away")
            print(f"  {date} | {home} {gh}-{ga} {away} | {status}")


if __name__ == "__main__":
    main()
