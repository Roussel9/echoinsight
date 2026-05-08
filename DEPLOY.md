# EchoInsight — Déploiement Vercel + Railway

## Architecture
- **Frontend (Next.js)** → Vercel (lien permanent)
- **Backend (FastAPI + Celery)** → Railway
- **Base de données (Postgres)** → Railway (plugin)
- **Redis** → Railway (plugin)

---

## Étape 1 — Mettre le projet sur GitHub

1. Va sur [github.com](https://github.com) → **New repository**
2. Nomme-le `echoinsight`, laisse-le **privé**
3. Dans le terminal, dans le dossier `echoinsight` :

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/TON_USERNAME/echoinsight.git
git push -u origin main
```

---

## Étape 2 — Déployer le backend sur Railway

1. Va sur [railway.app](https://railway.app) → **Login with GitHub**
2. **New Project** → **Deploy from GitHub repo** → sélectionne `echoinsight`
3. Quand Railway demande quel dossier : tape `apps/server`
4. Ajoute les plugins dans ton projet Railway :
   - Clique **+ New** → **Database** → **PostgreSQL**
   - Clique **+ New** → **Database** → **Redis**
5. Dans les **Variables** du service backend, ajoute :

| Variable | Valeur |
|---|---|
| `DATABASE_URL` | (copie depuis le plugin Postgres → **Connect** → `DATABASE_URL`) |
| `REDIS_URL` | (copie depuis le plugin Redis → **Connect** → `REDIS_URL`) |
| `OPENAI_API_KEY` | ta clé OpenAI (ou laisse vide si pas utilisé) |

6. Railway va déployer automatiquement. Une fois fait, copie l'URL publique du service (ex: `https://echoinsight-backend-production.up.railway.app`)

### Déployer le worker Celery (séparé)

1. Dans Railway, **+ New Service** → **GitHub repo** → `echoinsight`, dossier `apps/server`
2. Dans **Settings** → **Start Command**, mets :
   ```
   celery -A worker.celery_app worker --loglevel=info
   ```
3. Ajoute les mêmes variables `DATABASE_URL` et `REDIS_URL`

---

## Étape 3 — Déployer le frontend sur Vercel

1. Va sur [vercel.com](https://vercel.com) → **Add New Project**
2. Importe ton repo GitHub `echoinsight`
3. Dans **Root Directory**, mets : `apps/web`
4. Dans **Environment Variables**, ajoute :

| Variable | Valeur |
|---|---|
| `BACKEND_URL` | l'URL Railway copiée à l'étape 2 (sans slash final) |

5. Clique **Deploy** → Vercel te donne ton lien permanent 🎉

---

## Résultat

- **Ton lien Vercel** : `https://echoinsight.vercel.app` (permanent, sans Docker)
- **Backend Railway** : tourne 24h/24, géré automatiquement
- **Plus besoin de garder ton PC allumé**
