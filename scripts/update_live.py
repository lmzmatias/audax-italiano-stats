"""
update_live.py
Loop que actualiza solo el partido en vivo en docs/data/latest.json.
- Si hay partido en vivo: refresca cada 1 minuto (1 request/min a API-Football)
- Si no hay partido: chequea cada 5 minutos
- El historial (SerpAPI) NO se toca — se actualiza con update_latest.py

Uso:
    python scripts/update_live.py --apifootball-key TU_KEY

Variables de entorno (alternativa):
    APIFOOTBALL_KEY=TU_KEY python scripts/update_live.py

Detener: Ctrl+C
"""

import json
import os
import sys
import time
import argparse
from datetime import date
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "latest.json")
AUDAX_TEAM_ID = 2329
BASE_URL = "https://v3.football.api-sports.io"

INTERVAL_LIVE    = 60   # segundos entre refreshes cuando hay partido en vivo
INTERVAL_NO_LIVE = 300  # segundos entre chequeos cuando no hay partido


def get_api_key(args):
    key = args.apifootball_key or os.environ.get("APIFOOTBALL_KEY", "")
    if not key:
        print("ERROR: Se requiere APIFOOTBALL_KEY.")
        print("  Uso: python scripts/update_live.py --apifootball-key TU_KEY")
        sys.exit(1)
    return key


def fetch_live(api_key):
    url = f"{BASE_URL}/fixtures?team={AUDAX_TEAM_ID}&live=all"
    req = Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        print(f"  HTTPError {e.code}: {e.reason}")
        return None
    except URLError as e:
        print(f"  URLError: {e}")
        return None

    errors = data.get("errors", {})
    if errors:
        print("  API errors:", errors)
        return None

    fixtures = data.get("response", [])
    if not fixtures:
        return None

    f = fixtures[0]
    teams   = f.get("teams", {})
    goals   = f.get("goals", {})
    status  = f.get("fixture", {}).get("status", {})
    elapsed = status.get("elapsed")

    home_name  = teams.get("home", {}).get("name", "")
    away_name  = teams.get("away", {}).get("name", "")
    home_goals = goals.get("home", 0) or 0
    away_goals = goals.get("away", 0) or 0

    if "italiano" in home_name.lower() or "audax" in home_name.lower():
        score_audax, score_rival, rival = home_goals, away_goals, away_name
    else:
        score_audax, score_rival, rival = away_goals, home_goals, home_name

    return {
        "rival":       rival,
        "score_audax": score_audax,
        "score_rival": score_rival,
        "result":      "LIVE",
        "status":      "LIVE",
        "elapsed":     elapsed,
        "date":        str(date.today()),
    }


def load_json():
    path = os.path.abspath(OUTPUT_PATH)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data):
    path = os.path.abspath(OUTPUT_PATH)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Loop de actualización del partido en vivo.")
    parser.add_argument("--apifootball-key", default="", help="API key de api-sports.io")
    args = parser.parse_args()
    api_key = get_api_key(args)

    print("Iniciando loop de en vivo. Ctrl+C para detener.")
    print(f"  Intervalo con partido: {INTERVAL_LIVE}s | Sin partido: {INTERVAL_NO_LIVE}s")

    requests_used = 0

    while True:
        now = time.strftime("%H:%M:%S")
        live = fetch_live(api_key)
        requests_used += 1

        current = load_json()
        current["live"] = live

        if live:
            print(f"[{now}] EN VIVO: {live['rival']} | Audax {live['score_audax']}-{live['score_rival']} | {live['elapsed']}' | requests hoy: ~{requests_used}")
            save_json(current)
            time.sleep(INTERVAL_LIVE)
        else:
            # Si antes había partido en vivo y ahora no, limpiar
            if current.get("live") is not None:
                print(f"[{now}] Partido terminado. Limpiando live.")
                save_json(current)
            else:
                print(f"[{now}] Sin partido en vivo. Próximo chequeo en {INTERVAL_NO_LIVE}s | requests hoy: ~{requests_used}")
            time.sleep(INTERVAL_NO_LIVE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDetenido.")
