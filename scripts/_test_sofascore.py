"""
Explora qué datos devuelve el endpoint de fixtures en vivo de api-sports.io
incluyendo eventos (goles, tarjetas, cambios) y minuto del partido.
"""
import json
import argparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE_URL = "https://v3.football.api-sports.io"
AUDAX_TEAM_ID = 2329


def get(api_key, path):
    url = BASE_URL + path
    req = Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        print("HTTPError:", e.code, e.reason)
        return None
    except URLError as e:
        print("URLError:", e)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()
    key = args.api_key

    # 1. Fixtures en vivo con todos los campos disponibles
    print("=== /fixtures?team=2329&live=all ===")
    data = get(key, f"/fixtures?team={AUDAX_TEAM_ID}&live=all")
    if data:
        fixtures = data.get("response", [])
        print(f"Partidos en vivo: {len(fixtures)}")
        if fixtures:
            f = fixtures[0]
            fixture_id = f.get("fixture", {}).get("id")
            print(f"Fixture ID: {fixture_id}")
            print(f"Status: {f.get('fixture',{}).get('status',{})}")
            print(f"Goals: {f.get('goals')}")
            print(f"Score: {f.get('score')}")
            print(f"Teams: {f.get('teams',{}).get('home',{}).get('name')} vs {f.get('teams',{}).get('away',{}).get('name')}")

            # 2. Eventos del partido (goles, tarjetas, cambios) — endpoint separado
            print(f"\n=== /fixtures/events?fixture={fixture_id} ===")
            data2 = get(key, f"/fixtures/events?fixture={fixture_id}")
            if data2:
                errors = data2.get("errors", {})
                if errors:
                    print("  Errors:", errors)
                else:
                    events = data2.get("response", [])
                    print(f"  Eventos: {len(events)}")
                    for e in events:
                        minute = e.get("time", {}).get("elapsed")
                        extra  = e.get("time", {}).get("extra")
                        etype  = e.get("type")
                        detail = e.get("detail")
                        player = e.get("player", {}).get("name")
                        assist = e.get("assist", {}).get("name")
                        team   = e.get("team", {}).get("name")
                        min_str = f"{minute}+{extra}'" if extra else f"{minute}'"
                        print(f"  {min_str} [{etype}] {detail} — {player} ({team})" + (f" (asist: {assist})" if assist else ""))

            # 3. Estadísticas del partido
            print(f"\n=== /fixtures/statistics?fixture={fixture_id} ===")
            data3 = get(key, f"/fixtures/statistics?fixture={fixture_id}")
            if data3:
                errors = data3.get("errors", {})
                if errors:
                    print("  Errors:", errors)
                else:
                    stats = data3.get("response", [])
                    print(f"  Equipos con stats: {len(stats)}")
                    for team_stats in stats:
                        tname = team_stats.get("team", {}).get("name")
                        print(f"  {tname}:")
                        for s in team_stats.get("statistics", [])[:8]:
                            print(f"    {s.get('type')}: {s.get('value')}")
        else:
            print("No hay partido en vivo ahora.")
            # Buscar el último fixture para probar con ID real
            print("\n=== Buscando último fixture de Audax para probar eventos ===")
            data_last = get(key, f"/fixtures?team={AUDAX_TEAM_ID}&last=1")
            if data_last:
                fs = data_last.get("response", [])
                if fs:
                    fid = fs[0].get("fixture", {}).get("id")
                    print(f"Último fixture ID: {fid}")
                    data_ev = get(key, f"/fixtures/events?fixture={fid}")
                    if data_ev:
                        errors = data_ev.get("errors", {})
                        if errors:
                            print("  Errors:", errors)
                        else:
                            events = data_ev.get("response", [])
                            print(f"  Eventos: {len(events)}")
                            for e in events[:10]:
                                minute = e.get("time", {}).get("elapsed")
                                etype  = e.get("type")
                                detail = e.get("detail")
                                player = e.get("player", {}).get("name")
                                team   = e.get("team", {}).get("name")
                                print(f"  {minute}' [{etype}] {detail} — {player} ({team})")


if __name__ == "__main__":
    main()
