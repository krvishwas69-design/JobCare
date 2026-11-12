# JobCare — Hiring marketplace (Django API + web frontend)

```
jobcare/
├── backend/            Django 6 + Django REST Framework API
│   ├── jobcare_backend/   settings, urls, wsgi
│   ├── accounts/          employer accounts, token auth, credits, invoices
│   ├── jobs/              jobs, candidates, applications, reports, public API
│   ├── build.sh           build/release script (migrate, collectstatic)
│   └── .env.example       every environment variable explained
├── frontend/           employer portal and candidate job search (static, no build step)
├── render.yaml         one-click Render deployment (web service + Postgres)
└── DEPLOY.md           step-by-step deployment guide
```

## Run locally
```bash
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # Windows: copy .env.example .env
python manage.py migrate
python manage.py seed_candidates                      # optional sample candidates for local demos only
python manage.py createsuperuser                      # optional, for /admin/
python manage.py runserver
```
Open http://localhost:8000 - the API and the UI are served together. Create an account on the sign-in screen.

If you open the frontend separately with VS Code Live Preview (for example, on
`http://127.0.0.1:3000`), keep Django running in a second terminal from `backend`
with `python manage.py runserver`. The frontend sends API requests to
`http://localhost:8000`; local development must use `DEBUG=True` to allow that
frontend origin.

First run checklist (once): `python manage.py makemigrations --check` should print "No changes detected".
If it lists changes, run `python manage.py makemigrations` and commit the new files.

## What works
- Sign up / sign in with mobile number or email + password (token auth)
- Post, edit, duplicate, close, delete jobs; "Finish posting" activates a job with a credit or plan
- Candidate database with search; unlock a phone number for 1 database credit
- Credits & usage, reports (from real data), invoices with printable PDF
- Candidate job search and application flow; applicant profiles are not added to the searchable candidate database
- Django admin at `/admin/`

## Important limitations
- Razorpay checkout is integrated for credit and unlimited plans. Configure the provider's test keys and
  webhook in deployment before testing; use live keys only after test payments, refunds, invoices, and
  reconciliation have been verified. Keep `DEMO_PAYMENTS=False` in production.
- The candidate marketplace currently accepts applications without candidate accounts. Have the privacy
  notice and data-handling process reviewed and finalized before collecting real applicants.
- The candidate application consent is recorded, and applicant records are kept out of the searchable
  candidate database by default. Configure a reviewed privacy notice and support contact before public use.
- Sample candidates are not loaded by deployment builds. The seed command is only for local/private demos;
  never use sample profiles as real candidate listings.
- The support chat gives canned answers; there is no live agent.
- Branding: the UI uses the Job Care name.
