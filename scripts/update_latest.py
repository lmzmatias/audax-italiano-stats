"""
update_latest.py
- API-Football (api-sports.io): partido en vivo en tiempo real
- SerpAPI: historial de partidos recientes
Actualiza docs/data/latest.json.

Uso:
    python scripts/update_latest.py --serpapi-key TU_KEY --apifootball-key TU_KEY

Variables de entorno (alternativa):
    SERPAPI_KEY=... APIFOOTBALL_KEY=... python scripts/update_latest.py
"""

import json
import os
import sys
import argparse
import re
from datetime import date, datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "latest.json")
MAX_HISTORY = 10

AUDAX_TEAM_ID = 2329  # A. Italiano en api-sports.io

SERPAPI_QUERIES = [
    "Audax Italiano resultados 2026",
    "Audax Italiano partidos jugados",
    "Audax Italiano",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_api_keys(args):
    serpapi_key = args.serpapi_key or os.environ.get("SERPAPI_KEY", "")
    apifootball_key = args.apifootball_key or os.environ.get("APIFOOTBALL_KEY", "")
    if not serpapi_key:
        print("ERROR: Se requiere SERPAPI_KEY.")
        sys.exit(1)
    if not apifootball_key:
        print("ERROR: Se requiere APIFOOTBALL_KEY.")
        sys.exit(1)
    return serpapi_key, apifootball_key


def http_get_json(url, headers=None):
    req = Request(url, headers=headers or {})
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        print(f"  HTTPError {e.code}: {e.reason}")
        return None
    except URLError as e:
        print(f"  URLError: {e}")
        return None


def es_futuro(date_str):
    today = date.today()
    m = re.search(r"(\d{1,2})-(\d{2})$", date_str)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        try:
            return date(today.year, month, day) > today
        except ValueError:
            return False
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date() > today
        except ValueError:
            continue
    return False


# ── API-Football: partido en vivo ──────────────────────────────────────────────

def apifootball_get(api_key, path):
    url = f"https://v3.football.api-sports.io{path}"
    return http_get_json(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })


def fetch_live(apifootball_key):
    print("Consultando API-Football (en vivo)...")
    data = apifootball_get(apifootball_key, f"/fixtures?team={AUDAX_TEAM_ID}&live=all")
    if not data:
        return None

    errors = data.get("errors", {})
    if errors:
        print("  API errors:", errors)
        return None

    fixtures = data.get("response", [])
    if not fixtures:
        print("  Sin partido en vivo.")
        return None

    f = fixtures[0]
    fixture_id = f.get("fixture", {}).get("id")
    teams      = f.get("teams", {})
    goals      = f.get("goals", {})
    status     = f.get("fixture", {}).get("status", {})
    elapsed    = status.get("elapsed")
    extra      = status.get("extra")

    home_name  = teams.get("home", {}).get("name", "")
    away_name  = teams.get("away", {}).get("name", "")
    home_goals = goals.get("home", 0) or 0
    away_goals = goals.get("away", 0) or 0

    if "italiano" in home_name.lower() or "audax" in home_name.lower():
        score_audax, score_rival, rival = home_goals, away_goals, away_name
    else:
        score_audax, score_rival, rival = away_goals, home_goals, home_name

    print(f"  EN VIVO: {home_name} {home_goals}-{away_goals} {away_name} | {status.get('long')} {elapsed}'")

    # Eventos del partido
    events_parsed = []
    data2 = apifootball_get(apifootball_key, f"/fixtures/events?fixture={fixture_id}")
    if data2 and not data2.get("errors"):
        for e in data2.get("response", []):
            min_e   = e.get("time", {}).get("elapsed")
            extra_e = e.get("time", {}).get("extra")
            etype   = e.get("type", "")
            detail  = e.get("detail", "")
            player  = e.get("player", {}).get("name")
            assist  = e.get("assist", {}).get("name")
            team    = e.get("team", {}).get("name", "")
            is_audax = "italiano" in team.lower() or "audax" in team.lower()

            if etype == "Goal":
                event_type = "own_goal" if detail == "Own Goal" else ("penalty" if detail == "Penalty" else "goal")
            elif etype == "Card":
                event_type = "yellow_card" if "Yellow" in detail else ("red_card" if "Red" in detail else "card")
            elif etype == "subst":
                event_type = "substitution"
            else:
                event_type = etype.lower()

            events_parsed.append({
                "minute":   min_e,
                "extra":    extra_e,
                "type":     event_type,
                "player":   player,
                "assist":   assist if assist else None,
                "team":     team,
                "is_audax": is_audax,
            })
        print(f"  Eventos: {len(events_parsed)}")

    return {
        "fixture_id":  fixture_id,
        "rival":       rival,
        "home":        home_name,
        "away":        away_name,
        "score_audax": score_audax,
        "score_rival": score_rival,
        "result":      "LIVE",
        "status":      "LIVE",
        "status_long": status.get("long", ""),
        "elapsed":     elapsed,
        "extra":       extra,
        "events":      events_parsed,
        "date":        str(date.today()),
    }


# ── SerpAPI: historial ─────────────────────────────────────────────────────────

def fetch_serpapi(serpapi_key, query):
    from urllib.parse import urlencode
    params = urlencode({
        "q": query,
        "api_key": serpapi_key,
        "engine": "google",
        "hl": "es",
        "gl": "cl",
    })
    return http_get_json("https://serpapi.com/search.json?" + params)


def parse_serpapi_games(data):
    sports = data.get("sports_results", {})
    games  = sports.get("games", [])
    finished = []

    for g in games:
        status = g.get("status", "").upper()
        teams  = g.get("teams", [])
        if len(teams) < 2:
            continue

        audax_idx = next(
            (i for i, t in enumerate(teams) if "audax" in t.get("name", "").lower() or "italiano" in t.get("name", "").lower()),
            None
        )
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
            # SerpAPI raramente detecta en vivo; lo ignoramos (usamos API-Football)
            continue
        elif score_audax > score_rival:
            result_str = "Victoria"
            status_out = "FT"
        elif score_audax == score_rival:
            result_str = "Empate"
            status_out = "FT"
        else:
            result_str = "Derrota"
            status_out = "FT"

        finished.append({
            "rival":       rival,
            "score_audax": score_audax,
            "score_rival": score_rival,
            "result":      result_str,
            "status":      status_out,
            "date":        match_date,
        })

    return finished


def fetch_history(serpapi_key):
    all_finished = []

    for query in SERPAPI_QUERIES:
        print(f"Consultando SerpAPI: '{query}'...")
        raw = fetch_serpapi(serpapi_key, query)
        if not raw:
            continue

        finished = parse_serpapi_games(raw)

        for p in finished:
            if es_futuro(p["date"]):
                print(f"  [ignorado futuro] {p['date']} vs {p['rival']}")
                continue
            key = (p["rival"], p["score_audax"], p["score_rival"])
            if not any((x["rival"], x["score_audax"], x["score_rival"]) == key for x in all_finished):
                all_finished.append(p)

        print(f"  >> {len(finished)} partidos FT (acumulado: {len(all_finished)})")
        if len(all_finished) >= MAX_HISTORY:
            break

    return all_finished[:MAX_HISTORY]


HISTORY_INTERVAL = 12 * 60 * 60  # 12 horas en segundos


def run_once(serpapi_key, apifootball_key):
    live_game = fetch_live(apifootball_key)
    history   = fetch_history(serpapi_key)

    last_game     = history[0] if len(history) > 0 else None
    previous_game = history[1] if len(history) > 1 else None
    extra_history = history[2:] if len(history) > 2 else []

    out_path = os.path.abspath(OUTPUT_PATH)

    # standings se edita manualmente — nunca se sobreescribe desde aquí
    existing_standings = []
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                existing_standings = json.load(f).get("standings", [])
        except Exception:
            pass

    result = {
        "live":       live_game,
        "last":       last_game,
        "previous":   previous_game,
        "history":    extra_history,
        "standings":  existing_standings,
        "updated_at": str(date.today()),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\nActualizado:", out_path)
    print("  live:    ", live_game)
    print("  last:    ", last_game)
    print("  history: ", len(extra_history), "partidos adicionales")
    print("  updated: ", result["updated_at"])


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Actualiza latest.json.")
    parser.add_argument("--serpapi-key",     default="", help="API key de SerpAPI")
    parser.add_argument("--apifootball-key", default="", help="API key de api-sports.io")
    parser.add_argument("--loop", action="store_true",
                        help=f"Modo loop: actualiza historial cada {HISTORY_INTERVAL//3600}h automáticamente")
    args = parser.parse_args()

    serpapi_key, apifootball_key = get_api_keys(args)

    if args.loop:
        import time
        print(f"Modo loop activo. Historial se actualiza cada {HISTORY_INTERVAL//3600}h. Ctrl+C para detener.")
        while True:
            run_once(serpapi_key, apifootball_key)
            next_run = time.strftime("%H:%M:%S", time.localtime(time.time() + HISTORY_INTERVAL))
            print(f"Próxima actualización de historial: {next_run}")
            time.sleep(HISTORY_INTERVAL)
    else:
        run_once(serpapi_key, apifootball_key)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDetenido.")
