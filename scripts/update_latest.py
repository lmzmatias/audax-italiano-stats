"""
update_latest.py
Consulta SerpAPI para obtener los resultados recientes del Audax Italiano
y actualiza docs/data/latest.json.

Uso:
    python scripts/update_latest.py --api-key TU_API_KEY

Variables de entorno (alternativa):
    SERPAPI_KEY=TU_API_KEY python scripts/update_latest.py
"""

import json
import os
import sys
import argparse
from datetime import date
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError

QUERY = "Audax Italiano partido"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "latest.json")


def get_api_key(args):
    key = args.api_key or os.environ.get("SERPAPI_KEY", "")
    if not key:
        print("ERROR: Se requiere una API key de SerpAPI.")
        print("  Uso: python scripts/update_latest.py --api-key TU_KEY")
        print("  O:   SERPAPI_KEY=TU_KEY python scripts/update_latest.py")
        sys.exit(1)
    return key


def fetch_serpapi(api_key):
    params = urlencode({
        "q": QUERY,
        "api_key": api_key,
        "engine": "google",
        "hl": "es",
        "gl": "cl",
    })
    url = "https://serpapi.com/search.json?" + params
    try:
        with urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print("ERROR al conectar con SerpAPI:", e)
        sys.exit(1)


def parse_sports_results(data):
    """
    Extrae partido en vivo, último partido y partido anterior
    desde la respuesta de SerpAPI (bloque sports_results).
    Devuelve un dict con la estructura de latest.json.
    """
    sports = data.get("sports_results", {})
    games = sports.get("games", [])

    live_game = None
    last_game = None
    previous_game = None

    finished = []

    for g in games:
        status = g.get("status", "").upper()
        teams = g.get("teams", [])
        if len(teams) < 2:
            continue

        # Identificar cuál equipo es Audax
        audax_idx = None
        for i, t in enumerate(teams):
            if "audax" in t.get("name", "").lower():
                audax_idx = i
                break
        if audax_idx is None:
            continue

        rival_idx = 1 - audax_idx
        try:
            score_audax = int(teams[audax_idx].get("score", 0))
            score_rival = int(teams[rival_idx].get("score", 0))
        except (ValueError, TypeError):
            score_audax = 0
            score_rival = 0

        rival = teams[rival_idx].get("name", "Desconocido")
        match_date = g.get("date", str(date.today()))

        if "SUSPENDED" in status or "CANCELLED" in status:
            result_str = status
        elif score_audax > score_rival:
            result_str = "Victoria"
        elif score_audax == score_rival:
            result_str = "Empate"
        else:
            result_str = "Derrota"

        entry = {
            "rival": rival,
            "score_audax": score_audax,
            "score_rival": score_rival,
            "result": result_str,
            "status": "LIVE" if "LIVE" in status or "EN VIVO" in status else "FT",
            "date": match_date,
        }

        if "LIVE" in status or "EN VIVO" in status:
            live_game = entry
        else:
            finished.append(entry)

    if finished:
        last_game = finished[0]
        if len(finished) > 1:
            previous_game = finished[1]

    return {
        "live": live_game,
        "last": last_game,
        "previous": previous_game,
        "updated_at": str(date.today()),
    }


def main():
    parser = argparse.ArgumentParser(description="Actualiza latest.json desde SerpAPI.")
    parser.add_argument("--api-key", default="", help="API key de SerpAPI")
    args = parser.parse_args()

    api_key = get_api_key(args)
    print("Consultando SerpAPI...")
    raw = fetch_serpapi(api_key)

    result = parse_sports_results(raw)

    out_path = os.path.abspath(OUTPUT_PATH)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("Actualizado:", out_path)
    print("  live:    ", result["live"])
    print("  last:    ", result["last"])
    print("  previous:", result["previous"])
    print("  updated: ", result["updated_at"])


if __name__ == "__main__":
    main()
