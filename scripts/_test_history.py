import json
from urllib.request import urlopen, Request

key = '28de30c3fe74b611c3c5496a23e2d317'

def test(label, url):
    print(f'\n--- {label} ---')
    req = Request(url, headers={'x-apisports-key': key, 'Accept': 'application/json'})
    with urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode('utf-8'))
    errors = data.get('errors', {})
    results = data.get('response', [])
    remaining = data.get('parameters', {})
    print(f'  errors: {errors}')
    print(f'  results: {len(results)}')
    if results:
        f = results[0]
        print(f'  sample: {json.dumps(f.get("fixture", {}).get("status", {}))[:100]}')

test('season=2026', 'https://v3.football.api-sports.io/fixtures?team=2329&season=2026')
test('last=10',     'https://v3.football.api-sports.io/fixtures?team=2329&last=10')
test('next=5',      'https://v3.football.api-sports.io/fixtures?team=2329&next=5')
