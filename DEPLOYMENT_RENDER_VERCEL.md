# Deploy Guide (Render + Vercel)

## 1. Deploy Backend on Render
1. Open Render dashboard -> New -> Web Service.
2. Connect GitHub repo: `ommachhi/shriji-tiles`.
3. Render auto-detect (or use `render.yaml` from repo root).
4. Confirm service settings:
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

### Required Environment Variables (Render)
- `CORS_ORIGINS` = `https://your-vercel-domain.vercel.app`
- `CORS_ORIGIN_REGEX` = `^https?://([a-z0-9-]+\.)?vercel\.app$`
- `PRODUCT_CATALOG_IMAGES_DIR` = `./images`

Notes:
- First cold start can take time on free plan.
- Ensure backend URL responds at `/health` and `/search?q=120080&catalog=aquant`.

## 2. Deploy Frontend on Vercel
1. Open Vercel dashboard -> Add New Project.
2. Import GitHub repo: `ommachhi/shriji-tiles`.
3. Set project root directory to: `frontend`.
4. Framework preset: `Create React App`.
5. Build settings:
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: `build`

### Required Environment Variables (Vercel)
- `REACT_APP_BACKEND_URL` = `https://your-render-backend-url.onrender.com`

Deploy and open the Vercel URL.

## 3. Post-Deploy Checks
Run these checks from browser/API client:
1. Backend health: `https://your-render-backend-url.onrender.com/health`
2. Search API: `https://your-render-backend-url.onrender.com/search?q=120080&catalog=aquant`
3. Frontend search in UI for codes: `120080`, `75080`, `1434-600mm`.
4. Confirm images load and prices are correct.

## 4. If CORS Error Appears
1. Add exact Vercel domain in Render `CORS_ORIGINS`.
2. Redeploy backend service on Render.
3. Hard refresh frontend.

## 5. CI Safety (Already Added)
GitHub Actions workflow is included at:
- `.github/workflows/deploy-readiness.yml`

It checks backend import and frontend production build on push/PR.
