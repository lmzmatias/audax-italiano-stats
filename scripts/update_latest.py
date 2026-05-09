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
from datetime import date, datetime
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "latest.json")
MAX_HISTORY = 10

# Queries a intentar en orden hasta obtener suficientes partidos
QUERIES = [
    "Audax Italiano resultados 2026",
    "Audax Italiano partidos jugados",
    "Audax Italiano",
]


def get_api_key(args):
    key = args.api_key or os.environ.get("SERPAPI_KEY", "")
    if not key:
        print("ERROR: Se requiere una API key de SerpAPI.")
        print("  Uso: python scripts/update_latest.py --api-key TU_KEY")
        print("  O:   SERPAPI_KEY=TU_KEY python scripts/update_latest.py")
        sys.exit(1)
    return key


def fetch_serpapi(api_key, query):
    params = urlencode({
        "q": query,
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


def es_futuro(date_str):
    """
    Devuelve True si la fecha del partido es posterior a hoy.
    Soporta formatos: 'dd-mm', 'Lun, dd-mm', 'yyyy-mm-dd', 'd/m/yyyy'
    """
    today = date.today()
    # Extraer solo la parte dd-mm si viene con día de semana
    import re
    m = re.search(r'(\d{1,2})-(\d{2})$', date_str)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        try:
            partido_date = date(today.year, month, day)
            return partido_date > today
        except ValueError:
            return False
    # Formato yyyy-mm-dd
    try:
        partido_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return partido_date > today
    except ValueError:
        pass
    # Formato d/m/yyyy
    try:
        partido_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        return partido_date > today
    except ValueError:
        pass
    return False


def parse_sports_results(data):
    """
    Extrae partido en vivo y partidos terminados
    desde la respuesta de SerpAPI (bloque sports_results).
    """
    sports = data.get("sports_results", {})
    games  = sports.get("games", [])

    live_game = None
    finished  = []

    for g in games:
        status = g.get("status", "").upper()
        teams  = g.get("teams", [])
        if len(teams) < 2:
            continue

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

        rival      = teams[rival_idx].get("name", "Desconocido")
        match_date = g.get("date", str(date.today()))

        if "SUSPENDED" in status or "CANCELADO" in status or "CANCELLED" in status:
            result_str = status
            status_out = status
        elif "LIVE" in status or "EN VIVO" in status:
            result_str = "LIVE"
            status_out = "LIVE"
        elif score_audax > score_rival:
            result_str = "Victoria"
            status_out = "FT"
        elif score_audax == score_rival:
            result_str = "Empate"
            status_out = "FT"
        else:
            result_str = "Derrota"
            status_out = "FT"

        entry = {
            "rival":       rival,
            "score_audax": score_audax,
            "score_rival": score_rival,
            "result":      result_str,
            "status":      status_out,
            "date":        match_date,
        }

        if status_out == "LIVE":
            live_game = entry
        else:
            finished.append(entry)

    return live_game, finished, len(games)


def main():
    parser = argparse.ArgumentParser(description="Actualiza latest.json desde SerpAPI.")
    parser.add_argument("--api-key", default="", help="API key de SerpAPI")
    parser.add_argument("--debug", action="store_true", help="Mostrar respuesta cruda de SerpAPI")
    args = parser.parse_args()

    api_key = get_api_key(args)

    live_game = None
    all_finished = []

    for query in QUERIES:
        print(f"Consultando SerpAPI: '{query}'...")
        raw = fetch_serpapi(api_key, query)

        if args.debug:
            sports = raw.get("sports_results", {})
            print("  sports_results keys:", list(sports.keys()))
            games = sports.get("games", [])
            print(f"  games encontrados: {len(games)}")
            for g in games:
                print("   ", g.get("date"), g.get("status"), [t.get("name") for t in g.get("teams", [])])

        lv, finished, total = parse_sports_results(raw)
        if lv:
            live_game = lv
        # SerpAPI devuelve del más antiguo al más reciente: invertir
        for p in reversed(finished):
            # Ignorar partidos futuros
            if es_futuro(p["date"]):
                print(f"  [ignorado futuro] {p['date']} vs {p['rival']}")
                continue
            # Evitar duplicados por rival+marcador
            key = (p["rival"], p["score_audax"], p["score_rival"])
            if not any((x["rival"], x["score_audax"], x["score_rival"]) == key for x in all_finished):
                all_finished.append(p)

        print(f"  >> {len(finished)} partidos FT encontrados (total acumulado: {len(all_finished)})")
        if len(all_finished) >= MAX_HISTORY:
            break

    history = all_finished[:MAX_HISTORY]
    last_game     = history[0] if len(history) > 0 else None
    previous_game = history[1] if len(history) > 1 else None
    extra_history = history[2:] if len(history) > 2 else []

    result = {
        "live":       live_game,
        "last":       last_game,
        "previous":   previous_game,
        "history":    extra_history,
        "updated_at": str(date.today()),
    }

    out_path = os.path.abspath(OUTPUT_PATH)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\nActualizado:", out_path)
    print("  live:    ", live_game)
    print("  last:    ", last_game)
    print("  previous:", previous_game)
    print("  history: ", len(extra_history), "partidos adicionales")
    print("  updated: ", result["updated_at"])


if __name__ == "__main__":
    main()
