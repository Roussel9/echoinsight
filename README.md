## EchoInsight (Demo)

Ein lokales Fullstack-Demo-Projekt mit **öffentlichem Gratis-Link** via Cloudflare Tunnel.

### Start (ein Befehl)

1) Docker Desktop starten (Linux Engine / WSL2).
2) In diesem Ordner:

```bash
docker compose up -d --build
```

### Deinen öffentlichen Link bekommen

Die öffentliche URL steht in den Logs vom Service `tunnel`:

```bash
docker compose logs -f tunnel
```

Du siehst eine `trycloudflare.com` URL. Diese an deinen Boss schicken.

### Lokal öffnen

- Web: `http://localhost:3000`
- API: `http://localhost:8000/docs`

### Hinweis

Der Link ist **gratis**, aber nur online solange dein PC + Docker laufen.

