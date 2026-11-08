#!/usr/bin/env python3
"""Zet een Portainer web-editor stack om naar een Git (repository) stack uit deze repo.

Gebruik (op media4, via een python-container met host-netwerk):
  python3 migrate-stack.py <stacknaam> [<stacknaam> ...]

Omgevingsvariabelen:
  PORTAINER_URL     standaard http://localhost:9000
  PORTAINER_TOKEN   Portainer access token (verplicht)
  ENDPOINT_ID       standaard 2 (media4)
  ENV_DIR           map met <stack>.env bestanden, standaard /env
  GIT_TOKEN         alleen nodig als Portainer geen opgeslagen Git-credential heeft

Werking per stack:
  1. zoekt de bestaande stack; slaat over als die al uit Git komt
  2. leest <stack>.env en controleert dat alle variabelen uit .env.example gevuld zijn
  3. neemt de Git-authenticatie over van een bestaande Git-stack
  4. verwijdert de oude stack en maakt hem opnieuw aan met dezelfde naam uit de repo
"""
import json, os, sys, urllib.request, urllib.error

URL = os.environ.get('PORTAINER_URL', 'http://localhost:9000').rstrip('/')
TOKEN = os.environ.get('PORTAINER_TOKEN') or sys.exit('PORTAINER_TOKEN ontbreekt')
EP = int(os.environ.get('ENDPOINT_ID', '2'))
ENV_DIR = os.environ.get('ENV_DIR', '/env')
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_URL = 'https://github.com/bertdeelman/portainer-stacks'
FOLDER = {'dockerproxy': 'dockerproxy-media4'}


def api(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-API-Key': TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f'API-fout {e.code} bij {method} {path}: {e.read().decode()[:500]}')


def read_env(path):
    env = []
    for line in open(path):
        line = line.rstrip('\n')
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env.append({'name': k, 'value': v})
    return env


def git_auth(stacks):
    for s in stacks:
        g = s.get('GitConfig')
        if s.get('EndpointId') == EP and g and g.get('Authentication'):
            a = g['Authentication']
            if a.get('GitCredentialID'):
                return {'repositoryAuthentication': True, 'repositoryGitCredentialID': a['GitCredentialID']}
            if os.environ.get('GIT_TOKEN'):
                return {'repositoryAuthentication': True, 'repositoryUsername': a.get('Username', ''),
                        'repositoryPassword': os.environ['GIT_TOKEN']}
            sys.exit('Geen opgeslagen Git-credential gevonden; zet GIT_TOKEN (GitHub PAT) en probeer opnieuw.')
    sys.exit('Geen bestaande Git-stack gevonden om de authenticatie van over te nemen.')


def migrate(name, stacks, auth):
    old = next((s for s in stacks if s['Name'] == name and s.get('EndpointId') == EP), None)
    if old is None:
        print(f'[{name}] niet gevonden in Portainer, overgeslagen'); return
    if old.get('GitConfig'):
        print(f'[{name}] komt al uit Git, overgeslagen'); return
    folder = FOLDER.get(name, name)
    example = os.path.join(REPO_DIR, folder, '.env.example')
    envfile = os.path.join(ENV_DIR, f'{name}.env')
    if not os.path.exists(example):
        sys.exit(f'[{name}] {folder}/.env.example niet gevonden; doe eerst git pull')
    if not os.path.exists(envfile):
        sys.exit(f'[{name}] {envfile} niet gevonden')
    env = read_env(envfile)
    have = {e['name'] for e in env}
    need = {l.split('=', 1)[0] for l in open(example) if '=' in l}
    missing = sorted(need - have)
    if missing:
        sys.exit(f'[{name}] ontbrekende variabelen in {envfile}: {", ".join(missing)}')
    print(f'[{name}] oude stack {old["Id"]} verwijderen...')
    api('DELETE', f'/api/stacks/{old["Id"]}?endpointId={EP}')
    body = {'name': name, 'repositoryURL': REPO_URL, 'repositoryReferenceName': 'refs/heads/main',
            'composeFile': f'{folder}/docker-compose.yml', 'env': env, **auth}
    print(f'[{name}] nieuwe Git-stack aanmaken...')
    new = api('POST', f'/api/stacks/create/standalone/repository?endpointId={EP}', body)
    print(f'[{name}] klaar: stack {new["Id"]}, status {new.get("Status")}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    stacks = api('GET', '/api/stacks')
    auth = git_auth(stacks)
    for n in sys.argv[1:]:
        migrate(n, stacks, auth)
