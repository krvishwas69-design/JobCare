# Deploying JobCare

## Option A (recommended): one Render service for everything
Django serves both the API and the website, so there is no CORS setup.

1. Create a GitHub repository and push this whole `jobcare` folder to it
   (`git init && git add . && git commit -m "JobCare" && git branch -M main && git remote add origin <url> && git push -u origin main`).
2. Go to https://dashboard.render.com -> **New** -> **Blueprint** -> pick the repository.
   Render reads `render.yaml`, creates the Postgres database and the web service, and sets `SECRET_KEY` and `DATABASE_URL` for you.
3. When asked, fill in `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` (a strong password) to get an admin login.
4. Click **Apply**. The first build takes a few minutes. Your app is at `https://<service-name>.onrender.com`.
5. Check `https://<service-name>.onrender.com/healthz` returns `{"status": "ok"}`, then open the site and create an account.
6. Configure Razorpay test credentials in Render's environment (never commit or share the secret keys):
   `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`. In Razorpay, configure the
   webhook URL as `https://<service-name>.onrender.com/api/billing/razorpay/webhook/` for the
   `payment.captured` event, and enable automatic payment capture.
7. Test a complete checkout using Razorpay test mode before switching to live credentials. Keep
   `DEMO_PAYMENTS=false` and `SEED_DEMO_DATA=false`.
8. Before inviting real candidates, publish a reviewed privacy notice with your business/contact
   details and retention/deletion process. The application consent checkbox is not a substitute for it.

Free-tier notes: free web services sleep when idle (first request after a pause is slow), and free databases have
usage/expiry limits - check Render's current terms. To use another Postgres (Neon, Supabase), delete the `databases:`
block in `render.yaml` and set `DATABASE_URL` yourself in the dashboard.

Custom domain: add it in Render, then set `ALLOWED_HOSTS=yourdomain.com` and
`CSRF_TRUSTED_ORIGINS=https://yourdomain.com` in the service's environment.

## Option B: frontend on Netlify/Vercel, API on Render
1. Deploy the backend as in Option A.
2. In `frontend/js/config.js` set `API_BASE` to your Render URL (e.g. `"https://jobcare.onrender.com"`).
3. Deploy the `frontend` folder to Netlify (publish directory `.`, no build command) or Vercel.
4. In Render -> Environment add `CORS_ALLOWED_ORIGINS=https://your-site.netlify.app` and
   `CSRF_TRUSTED_ORIGINS=https://your-site.netlify.app`, then redeploy.

Production builds do not load sample candidates. Keep `SEED_DEMO_DATA=false` in production.
The Render blueprint sets `DEMO_PAYMENTS=false`; configure and test Razorpay before enabling purchases
for customers. If payment keys are not set, checkout is unavailable and purchases are not granted.

## Moving your old SQLite data
Do not deploy `db.sqlite3` or `.env`. Production candidate records should be added only with appropriate
permission; sample profiles can be loaded explicitly for a private demo with `SEED_DEMO_DATA=true`.

## Environment variables
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | required in production (Render generates it) |
| `DEBUG` | `False` in production |
| `DATABASE_URL` | Postgres connection URL |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | comma-separated; Render's own hostname is added automatically |
| `DEMO_PAYMENTS` | Keep `False` in production; simulated purchases are only for private demos |
| `SEED_DEMO_DATA` | Set `true` only for local/private demo deployments; production should use `false` |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Razorpay API credentials; store in the hosting provider's secret environment |
| `RAZORPAY_WEBHOOK_SECRET` | Secret configured for the Razorpay `payment.captured` webhook |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` / `_EMAIL` | auto-create an admin during the build |
