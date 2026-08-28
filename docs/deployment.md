# Deployment guide

Target: recruiters try the live demo with zero local setup. Recommended split:
**Railway** for the backend (Docker; Playwright needs a real container) and
**Vercel** for the frontend (native Next.js hosting). Both have workable free
or hobby tiers.

## Backend → Railway

1. Push this repo to GitHub (Railway deploys from a repo).
2. Railway → New Project → Deploy from GitHub repo → set **Root Directory**
   to `backend/` (it will pick up `backend/Dockerfile`).
3. Environment variables:
   - `ANTHROPIC_API_KEY` — production key (create a separate key so it can be
     revoked independently; set a monthly spend limit in the Anthropic console)
   - `SEARCH_API_KEY` — Tavily key
   - `FRONTEND_ORIGIN` — the Vercel URL once known, e.g.
     `https://your-app.vercel.app`
4. Optional but recommended: attach a **volume** mounted at `/app` data path
   so report links survive redeploys (SQLite lives in the container FS).
   Without a volume, reports are ephemeral per deploy — acceptable for a demo.
5. Note the public URL Railway assigns, e.g. `https://ci-backend.up.railway.app`.

## Frontend → Vercel

1. Vercel → New Project → import the repo → set **Root Directory** to
   `frontend/`.
2. Environment variable: `NEXT_PUBLIC_API_URL` = the Railway backend URL.
3. Deploy; then set `FRONTEND_ORIGIN` on Railway to the Vercel URL and
   redeploy the backend (CORS).

## Post-deploy checklist

- [ ] `GET {backend}/api/health` returns ok
- [ ] Full run from the deployed frontend on a fresh product URL
- [ ] Citations open correct sources from the deployed report page
- [ ] Report link still works after a page refresh (and after redeploy, if
      volume attached)
- [ ] Update the README's live-demo link
- [ ] Spend limit set on the production Anthropic key (each report ≈ $0.36;
      a public demo can be driven by strangers — consider a Railway sleep
      schedule or basic rate limit if traffic appears)

## Costs

- Railway hobby: ~$5/mo; Vercel hobby: free.
- Model + search: ~$0.36 per report run by visitors.
