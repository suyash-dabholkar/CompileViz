# Deployment

Two services, deployed separately: the backend (FastAPI) on Render, the
frontend (React/Vite) on Vercel. This is the standard split for an app
shaped like this one, and it's what was decided early in this project.

Vercel is not a good fit for the backend: it's built around short-lived
serverless functions, while this backend needs a persistent FastAPI
process. Render (or Railway, as an equally valid alternative) runs a
real, always-on process, exactly what's needed here, with no code
restructuring required.

## Step 1: Deploy the backend to Render

1. Push your latest `main` to GitHub if you haven't already.
2. Go to [render.com](https://render.com) and sign in with GitHub.
3. Click **New +** → **Web Service**, and connect the `compileviz`
   repo.
4. Render should detect `render.yaml` at the repo root and offer to use
   it (click **Apply**). If it doesn't pick it up automatically, fill
   the fields in by hand instead:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
5. Click **Create Web Service**. The first deploy takes a few minutes,
   watch the build log for errors (the same kind you'd see running
   `pip install` locally).
6. Once it's live, Render gives you a URL like
   `https://compileviz-backend.onrender.com`. **Copy this down**, you
   need it in Step 2.
7. Confirm it actually works: visit
   `https://compileviz-backend.onrender.com/health` in your browser.
   You should see `{"status":"ok","service":"compileviz-backend"}`.

A note on Render's free tier: it spins the service down after 15
minutes of no traffic, and the next request has to wake it back up,
which takes 30-60 seconds. That first slow request is normal, not a
bug. If you're demoing live, open the health check URL a minute before
you start presenting, so it's already warm.

### Alternative: Railway instead of Render

If you'd rather use Railway: same idea, no `render.yaml` needed.
1. Go to [railway.app](https://railway.app), sign in with GitHub, **New
   Project** → **Deploy from GitHub repo**.
2. Set the root directory to `backend` in the service's Settings.
3. Railway auto-detects Python; if it asks for a start command, use
   the same one: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Railway gives you a public URL the same way Render does, once you
   enable networking for the service (Settings → Networking → Generate
   Domain).

## Step 2: Deploy the frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New** → **Project**, and import the `compileviz` repo.
3. Vercel auto-detects Vite, but double check these fields:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
4. Before clicking Deploy, expand **Environment Variables** and add:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: the Render backend URL from Step 1, e.g.
     `https://compileviz-backend.onrender.com` (no trailing slash)
5. Click **Deploy**. Vercel gives you a URL like
   `https://compileviz.vercel.app` once it's done.

## Step 3: Connect them (fix CORS)

At this point, your frontend can technically reach your backend, but
the backend's CORS settings only allow `localhost`, so it'll reject
the deployed frontend's requests. Fix this on Render:

1. Go to your backend service on Render → **Environment**.
2. Add an environment variable:
   - **Key**: `ALLOWED_ORIGINS`
   - **Value**: your Vercel URL from Step 2, e.g.
     `https://compileviz.vercel.app`
   - If Vercel also gave you preview-deployment URLs you want to allow,
     add them comma-separated: `https://compileviz.vercel.app,https://compileviz-git-main-yourname.vercel.app`
3. Save, Render redeploys automatically with the new setting (this
   is exactly what `app/main.py`'s `ALLOWED_ORIGINS` handling from
   this milestone is for).

## Step 4: Verify the live app end to end

1. Open your Vercel URL.
2. Check the footer says `backend: ok`, not `unreachable`. If it's
   stuck checking, give it a minute, that's Render's free tier waking
   up (see the note in Step 1).
3. Click through all four tabs and run something in each: build a
   regex, analyze a grammar, minimize a DFA, compile and run a
   program. If any of them show a CORS error in the browser console,
   double check the exact URL in `ALLOWED_ORIGINS` matches your
   Vercel URL exactly (including `https://`, no trailing slash).

## Redeploying after future changes

Both Render and Vercel auto-deploy on every push to `main` by default,
once this initial setup is done, merging a PR is all it takes to ship
an update to the live site.
