#!/usr/bin/env python3
"""Zet of wijzig omgevingsvariabelen van Git-stacks in Portainer en redeploy ze.

Gebruik:
  python3 set-env.py KEY=VALUE [KEY=VALUE ...] -- <stack>[@endpointId] [<stack> ...]

Voorbeeld:
  python3 set-env.py HOMEPAGE_HOST=media4.local -- spoolman partdb dockerproxy@2
  python3 set-env.py -- spoolman partdb      (zonder KEY=VALUE: alleen pull en redeploy)

Omgevingsvariabelen: PORTAINER_URL (standaard http://localhost:9000), PORTAINER_TOKEN, GIT_TOKEN.
Een stack wordt alleen opnieuw gedeployed als er echt iets verandert.
"""
import json, os, sys, urllib.request, urllib.error

URL = os.environ.get('PORTAINER_URL', 'http://localhost:9000').rstrip('/')
TOKEN = os.environ.get('PORTAINER_TOKEN') or sys.exit('PORTAINER_TOKEN ontbreekt')
GIT_TOKEN = os.environ.get('GIT_TOKEN') or sys.exit('GIT_TOKEN ontbreekt')


def api(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-API-Key': TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f'API-fout {e.code} bij {method} {path}: {e.read().decode()[:500]}')


if '--' not in sys.argv:
    sys.exit(__doc__)
i = sys.argv.index('--')
updates = dict(a.split('=', 1) for a in sys.argv[1:i])
targets = sys.argv[i + 1:]
stacks = api('GET', '/api/stacks')

for t in targets:
    name, _, ep = t.partition('@')
    found = [s for s in stacks if s['Name'] == name and (not ep or s['EndpointId'] == int(ep))]
    if len(found) != 1:
        print(f'[{t}] {len(found)} stacks gevonden ({[s["EndpointId"] for s in found]}); gebruik naam@endpointId'); continue
    s = found[0]
    if not s.get('GitConfig'):
        print(f'[{t}] geen Git-stack, overgeslagen'); continue
    env = {e['name']: e['value'] for e in (s.get('Env') or [])}
    changed = {k: v for k, v in updates.items() if env.get(k) != v}
    if updates and not changed:
        print(f'[{t}] al goed, overgeslagen'); continue
    env.update(changed)
    auth = (s['GitConfig'].get('Authentication') or {})
    body = {'env': [{'name': k, 'value': v} for k, v in env.items()], 'prune': False, 'pullImage': False,
            'repositoryReferenceName': s['GitConfig'].get('ReferenceName') or 'refs/heads/main',
            'repositoryAuthentication': True, 'repositoryUsername': auth.get('Username', ''),
            'repositoryPassword': GIT_TOKEN}
    print(f'[{t}] {", ".join(changed) or "pull"} bijwerken en redeployen...')
    api('PUT', f'/api/stacks/{s["Id"]}/git/redeploy?endpointId={s["EndpointId"]}', body)
    print(f'[{t}] klaar')
