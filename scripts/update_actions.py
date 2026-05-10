"""
update_actions.py
Script diseñado para correr en GitHub Actions cada 5 minutos.

Lógica:
  1. Fuera de 12:00-22:00 hora Chile → no hace nada.
  2. Si el JSON dice que había partido en vivo (live != null) → consulta API-Football
     cada 5 min (el workflow corre cada 5 min).
  3. Si no había partido en vivo → consulta API-Football cada 15 min para detectar
     si empezó uno. Si detecta partido, pasa al modo cada 5 min.
  4. Si no hay partido y han pasado ≥60 min desde la última actualización de
     historial → actualiza historial con SerpAPI.

Consumo estimado de API-Football (100 req/día límite Free):
  - Sin partido: 1 req/15min × 10h = 40 req/día
  - Con partido (90 min): 1 req/5min × 90min = 18 req/partido
  - Total día con 1 partido: ~58 req → dentro del límite ✓

Variables de entorno requeridas (GitHub Secrets):
  APIFOOTBALL_KEY
  SERPAPI_KEY
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "latest.json")
AUDAX_TEAM_ID = 2329
BASE_URL = "https://v3.football.api-sports.io"

# Hora Chile = UTC-4 (sin DST en invierno, UTC-3 en verano — usamos UTC-4 como base)
CHILE_TZ = timezone(timedelta(hours=-4))
HORA_INICIO = 12  # 12:00 hora Chile
HORA_FIN    = 22  # 22:00 hora Chile
HISTORY_INTERVAL_MIN  = 60  # minutos entre actualizaciones de historial con SerpAPI
LIVE_CHECK_INTERVAL   = 15  # minutos entre checks de API-Football cuando no hay partido


def get_keys():
    apifootball_key = os.environ.get("APIFOOTBALL_KEY", "")
    serpapi_key     = os.environ.get("SERPAPI_KEY", "")
    if not apifootball_key:
        print("ERROR: APIFOOTBALL_KEY no configurada.")
        sys.exit(1)
    if not serpapi_key:
        print("ERROR: SERPAPI_KEY no configurada.")
        sys.exit(1)
    return apifootball_key, serpapi_key


def hora_chile():
    return datetime.now(CHILE_TZ)


def en_horario_activo():
    h = hora_chile().hour
    return HORA_INICIO <= h < HORA_FIN


def api_get(api_key, path):
    url = BASE_URL + path
    req = Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError) as e:
        print(f"  Error API-Football: {e}")
        return None


def fetch_live(api_key):
    data = api_get(api_key, f"/fixtures?team={AUDAX_TEAM_ID}&live=all")
    if not data or data.get("errors"):
        return None
    fixtures = data.get("response", [])
    if not fixtures:
        return None

    f = fixtures[0]
    fixture_id  = f.get("fixture", {}).get("id")
    teams       = f.get("teams", {})
    goals       = f.get("goals", {})
    status      = f.get("fixture", {}).get("status", {})
    elapsed     = status.get("elapsed")
    extra       = status.get("extra")
    status_long = status.get("long", "")

    home_name  = teams.get("home", {}).get("name", "")
    away_name  = teams.get("away", {}).get("name", "")
    home_goals = goals.get("home", 0) or 0
    away_goals = goals.get("away", 0) or 0

    if "italiano" in home_name.lower() or "audax" in home_name.lower():
        score_audax, score_rival, rival = home_goals, away_goals, away_name
    else:
        score_audax, score_rival, rival = away_goals, home_goals, home_name

    print(f"  EN VIVO: {home_name} {home_goals}-{away_goals} {away_name} | {status_long} {elapsed}'")

    # Eventos
    events_parsed = []
    data2 = api_get(api_key, f"/fixtures/events?fixture={fixture_id}")
    if data2 and not data2.get("errors"):
        for e in data2.get("response", []):
            min_e    = e.get("time", {}).get("elapsed")
            extra_e  = e.get("time", {}).get("extra")
            etype    = e.get("type", "")
            detail   = e.get("detail", "")
            player   = e.get("player", {}).get("name")
            assist   = e.get("assist", {}).get("name")
            team     = e.get("team", {}).get("name", "")
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
        "date":        hora_chile().strftime("%Y-%m-%d"),
    }


def fetch_history(serpapi_key):
    """Reutiliza la lógica de update_latest.py importándola."""
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "update_latest",
        pathlib.Path(__file__).parent / "update_latest.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.fetch_history(serpapi_key)


def load_json():
    path = os.path.abspath(OUTPUT_PATH)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data):
    path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


ISO_FMT = "%Y-%m-%dT%H:%M"


def minutos_desde(ts_str):
    """Devuelve minutos desde un timestamp ISO, o 999 si no hay dato."""
    if not ts_str:
        return 999
    try:
        last = datetime.strptime(ts_str[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=CHILE_TZ)
        return (hora_chile() - last).total_seconds() / 60
    except Exception:
        return 999


def main():
    apifootball_key, serpapi_key = get_keys()
    now = hora_chile()
    print(f"Hora Chile: {now.strftime('%H:%M')} | Horario activo: {en_horario_activo()}")

    current = load_json()

    # ── Fuera de horario: no hacer nada ──────────────────────────────
    if not en_horario_activo():
        print("Fuera de horario (12:00-22:00 Chile). Sin acción.")
        return

    habia_partido = bool(current.get("live"))
    mins_desde_check = minutos_desde(current.get("last_live_check"))

    # ── Decidir si consultar API-Football ────────────────────────────
    # Si había partido en vivo → siempre consultar (cada 5 min del workflow)
    # Si no había partido → consultar solo cada 15 min
    debe_consultar_live = habia_partido or (mins_desde_check >= LIVE_CHECK_INTERVAL)

    if debe_consultar_live:
        print(f"Consultando API-Football (en vivo)... [había partido: {habia_partido}, hace {int(mins_desde_check)} min]")
        live = fetch_live(apifootball_key)
        current["last_live_check"] = now.strftime(ISO_FMT)

        if live:
            current["live"] = live
            save_json(current)
            print("  JSON actualizado con partido en vivo.")
            return

        # No hay partido en vivo
        current["live"] = None
        print("  Sin partido en vivo.")
    else:
        print(f"  Saltando check de en vivo (último hace {int(mins_desde_check)} min, umbral {LIVE_CHECK_INTERVAL} min).")

    # ── Actualizar historial si han pasado ≥60 min ────────────────────
    mins_hist = minutos_desde(current.get("last_history_update"))
    print(f"  Última actualización de historial: hace ~{int(mins_hist)} min")

    if mins_hist >= HISTORY_INTERVAL_MIN:
        print("  Actualizando historial con SerpAPI...")
        history = fetch_history(serpapi_key)
        last_game     = history[0] if len(history) > 0 else None
        previous_game = history[1] if len(history) > 1 else None
        extra_history = history[2:] if len(history) > 2 else []

        current["last"]                = last_game
        current["previous"]            = previous_game
        current["history"]             = extra_history
        current["last_history_update"] = now.strftime(ISO_FMT)
        print(f"  Historial actualizado: {len(history)} partidos.")
        # standings se edita manualmente en latest.json — no se toca aquí
        save_json(current)
    else:
        print(f"  Historial reciente (< {HISTORY_INTERVAL_MIN} min). Sin acción.")
        save_json(current)


if __name__ == "__main__":
    main()
