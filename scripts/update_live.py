"""
update_live.py
Loop que actualiza el partido en vivo en docs/data/latest.json.
- Si hay partido en vivo: refresca cada 2 minutos (2 requests/ciclo a API-Football)
  * /fixtures?team=2329&live=all  → marcador + minuto
  * /fixtures/events?fixture=ID   → goles, tarjetas, cambios
- Si no hay partido: chequea cada 5 minutos (1 request/ciclo)
- El historial (SerpAPI) NO se toca — se actualiza con update_latest.py

Consumo estimado: ~90 requests por partido de 90 min (dentro del límite de 100/día)

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
from datetime import date, datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "latest.json")
AUDAX_TEAM_ID = 2329
BASE_URL = "https://v3.football.api-sports.io"

INTERVAL_LIVE    = 120  # 2 minutos — 2 requests/ciclo → ~90 requests/partido
INTERVAL_NO_LIVE = 300  # 5 minutos cuando no hay partido
INTERVAL_SLEEP   = 60   # 1 minuto de espera cuando estamos fuera de horario

CHILE_TZ   = timezone(timedelta(hours=-4))
HORA_INICIO = 12  # 12:00 hora Chile
HORA_FIN    = 22  # 22:00 hora Chile


def en_horario_activo():
    return HORA_INICIO <= datetime.now(CHILE_TZ).hour < HORA_FIN


def get_api_key(args):
    key = args.apifootball_key or os.environ.get("APIFOOTBALL_KEY", "")
    if not key:
        print("ERROR: Se requiere APIFOOTBALL_KEY.")
        print("  Uso: python scripts/update_live.py --apifootball-key TU_KEY")
        sys.exit(1)
    return key


def api_get(api_key, path):
    url = BASE_URL + path
    req = Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        print(f"  HTTPError {e.code}: {e.reason}")
        return None
    except URLError as e:
        print(f"  URLError: {e}")
        return None


def fetch_live_with_events(api_key):
    """
    Devuelve dict con datos del partido en vivo + lista de eventos,
    o None si no hay partido.
    Consume 2 requests si hay partido, 1 si no hay.
    """
    # Request 1: fixture en vivo
    data = api_get(api_key, f"/fixtures?team={AUDAX_TEAM_ID}&live=all")
    if not data:
        return None

    errors = data.get("errors", {})
    if errors:
        print("  API errors:", errors)
        return None

    fixtures = data.get("response", [])
    if not fixtures:
        return None

    f = fixtures[0]
    fixture_id = f.get("fixture", {}).get("id")
    teams      = f.get("teams", {})
    goals      = f.get("goals", {})
    status     = f.get("fixture", {}).get("status", {})
    elapsed    = status.get("elapsed")
    extra      = status.get("extra")
    status_long = status.get("long", "")

    home_name  = teams.get("home", {}).get("name", "")
    away_name  = teams.get("away", {}).get("name", "")
    home_goals = goals.get("home", 0) or 0
    away_goals = goals.get("away", 0) or 0

    if "italiano" in home_name.lower() or "audax" in home_name.lower():
        score_audax, score_rival, rival = home_goals, away_goals, away_name
        audax_home = True
    else:
        score_audax, score_rival, rival = away_goals, home_goals, home_name
        audax_home = False

    # Request 2: eventos del partido
    events_parsed = []
    data2 = api_get(api_key, f"/fixtures/events?fixture={fixture_id}")
    if data2 and not data2.get("errors"):
        for e in data2.get("response", []):
            min_e   = e.get("time", {}).get("elapsed")
            extra_e = e.get("time", {}).get("extra")
            etype   = e.get("type", "")
            detail  = e.get("detail", "")
            player  = e.get("player", {}).get("name")
            assist  = e.get("assist", {}).get("name")
            team    = e.get("team", {}).get("name", "")

            # Determinar si el evento es de Audax o del rival
            is_audax = "italiano" in team.lower() or "audax" in team.lower()

            # Normalizar tipo
            if etype == "Goal":
                if detail == "Own Goal":
                    event_type = "own_goal"
                elif detail == "Penalty":
                    event_type = "penalty"
                else:
                    event_type = "goal"
            elif etype == "Card":
                if "Yellow" in detail:
                    event_type = "yellow_card"
                elif "Red" in detail:
                    event_type = "red_card"
                else:
                    event_type = "card"
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

    return {
        "fixture_id":  fixture_id,
        "rival":       rival,
        "home":        home_name,
        "away":        away_name,
        "score_audax": score_audax,
        "score_rival": score_rival,
        "result":      "LIVE",
        "status":      "LIVE",
        "status_long": status_long,
        "elapsed":     elapsed,
        "extra":       extra,
        "events":      events_parsed,
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
    print(f"  Con partido: cada {INTERVAL_LIVE}s (2 req/ciclo) | Sin partido: cada {INTERVAL_NO_LIVE}s (1 req/ciclo)")

    requests_used = 0

    while True:
        now = time.strftime("%H:%M:%S")

        # ── Fuera de horario: no consultar la API ──────────────────
        if not en_horario_activo():
            print(f"[{now}] Fuera de horario (12:00-22:00 Chile). Esperando {INTERVAL_SLEEP}s...")
            time.sleep(INTERVAL_SLEEP)
            continue

        live = fetch_live_with_events(api_key)
        requests_used += 2 if live else 1

        current = load_json()
        current["live"] = live

        if live:
            min_str = f"{live['elapsed']}+{live['extra']}'" if live.get("extra") else f"{live['elapsed']}'"
            goals_count = sum(1 for e in live["events"] if e["type"] in ("goal", "penalty", "own_goal"))
            cards_count = sum(1 for e in live["events"] if "card" in e["type"])
            print(f"[{now}] EN VIVO {min_str} | {live['home']} {live['score_audax'] if 'italiano' in live['home'].lower() or 'audax' in live['home'].lower() else live['score_rival']}-{live['score_rival'] if 'italiano' in live['home'].lower() or 'audax' in live['home'].lower() else live['score_audax']} {live['away']} | goles:{goals_count} tarjetas:{cards_count} | req~{requests_used}")
            save_json(current)
            time.sleep(INTERVAL_LIVE)
        else:
            if current.get("live") is not None:
                print(f"[{now}] Partido terminado. Limpiando live.")
                save_json(current)
            else:
                print(f"[{now}] Sin partido en vivo. Próximo chequeo en {INTERVAL_NO_LIVE}s | req~{requests_used}")
            time.sleep(INTERVAL_NO_LIVE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDetenido.")
