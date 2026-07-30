# portainer-stacks

Git-repo met Docker Compose stacks voor Portainer op media4, gedeployed via Portainer's GitOps (Repository build method).

## Structuur

```
portainer-stacks/
├── .gitignore
├── README.md
└── <stack-naam>/
    ├── docker-compose.yml
    └── .env.example
```

Elke stack heeft zijn eigen submap met een `docker-compose.yml` en een `.env.example`. De echte waardes komen **niet** in Git terecht, die beheert Portainer zelf via `stack.env`.

## Wat wel en niet naar Git gaat

| Bestand | Naar Git? | Doel |
|---|---|---|
| `docker-compose.yml` | Ja | De stack-definitie, met `${VAR}` placeholders zonder fallback-waarde |
| `.env.example` | Ja | Documentatie: welke variabelen verwacht de stack (namen, geen waardes) |
| `.env` | Nee | Lokaal testbestand op media4, genegeerd via `.gitignore` |
| `stack.env` | Nee | Door Portainer zelf aangemaakt/beheerd bij deployment, genegeerd via `.gitignore` |

## Belangrijk: geen fallback-waardes in de compose file

Gebruik altijd `${VAR}` zonder `:-default`. Geen enkele waarde (ook geen "onschuldige" zoals een netwerknaam) staat vast in de compose file. Reden: ook in een privé repo wil je geen infrastructuur-namen of instellingen hardcoded hebben staan. Ontbreekt een variabele bij deployment, dan faalt Portainer met een duidelijke foutmelding, dat is bewust gedrag: liever een expliciete fout dan een stille verkeerde default.

## Nieuwe stack toevoegen

1. Maak een submap aan:
   ```bash
   cd /volume2/projects/portainer-stacks
   mkdir <stack-naam>
   cd <stack-naam>
   ```

2. Maak `docker-compose.yml`, gebruik `${VAR}` zonder fallback voor elke instelbare waarde (poorten, tags, netwerk, timezone):
   ```yaml
   services:
     mijn-service:
       image: voorbeeld/image:${IMAGE_TAG}
       ports:
         - "${SERVICE_PORT}:80"
       network_mode: ${DOCKER_NETWORK}
       environment:
         - TZ=${TZ}
   ```

3. Maak `.env.example` met dezelfde variabelen, zonder waardes, puur als documentatie:
   ```bash
   cat > .env.example << 'EOF'
   IMAGE_TAG=
   SERVICE_PORT=
   DOCKER_NETWORK=
   TZ=
   EOF
   ```

4. Maak lokaal je eigen `.env` met de echte waardes (blijft op media4, gaat nooit naar Git):
   ```bash
   cat > .env << 'EOF'
   IMAGE_TAG=latest
   SERVICE_PORT=8080
   DOCKER_NETWORK=deellan
   TZ=Europe/Amsterdam
   EOF
   ```

5. Commit en push:
   ```bash
   cd /volume2/projects/portainer-stacks
   git add <stack-naam>/docker-compose.yml <stack-naam>/.env.example
   git status   # check dat er geen .env of stack.env tussen staat
   git commit -m "Add <stack-naam> stack"
   git push
   ```

6. Maak de stack aan in Portainer:
   - **Stacks > Add stack**
   - **Name**: `<stack-naam>`
   - **Build method**: Repository
   - **Authentication**: aan, met GitHub username + Personal Access Token
   - **Repository URL**: `https://github.com/bertdeelman/portainer-stacks.git`
   - **Repository reference**: `refs/heads/main`
   - **Compose path**: `<stack-naam>/docker-compose.yml`
   - **Environment variables**: vul hier de waardes in uit je `.env.example` (dit wordt Portainer's `stack.env`)
   - **Deploy the stack**

## Bestaande stack aanpassen

- Wijzig `docker-compose.yml` in de repo, commit en push.
- In Portainer: open de stack > **Pull and redeploy** (of wacht op GitOps updates als die aanstaat).
- Wijzig je een environment variable (waarde, niet de variabele zelf): pas aan via Portainer > Stack > **Editor** tab, niet via Git.

## Eenmalige setup (al gedaan op media4)

```bash
git config --global user.email "bdeelman@gmail.com"
git config --global user.name "Bert Deelman"
git config --global credential.helper store
```

Bij de eerste push per sessie: GitHub username (`bertdeelman`) + Personal Access Token als wachtwoord (geen normaal GitHub-wachtwoord, dat werkt niet meer voor Git over HTTPS).
