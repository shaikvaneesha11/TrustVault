# TrustVault

My submission for the Snovasys hiring challenge. It is a document sharing app
where a document can only be opened by people who were given access, and every
open, including the refused ones, is saved in an audit log.

Live site: https://trustvault-0wp7.onrender.com
It runs on a free plan, so the first load can take about a minute.
Demo video: https://drive.google.com/file/d/13PbWPepe3n1n5l8L6NDoPLTphMzsCtMA/view

## Demo logins
The password for all of them is Demo-Pass-2026. They hold no real data.

- Admin: admin@trustvault.demo
- Owner: owner@trustvault.demo
- Second owner: owner2@trustvault.demo
- Viewer: viewer@trustvault.demo

After 5 wrong passwords an account is locked for 15 minutes. If that happens,
wait or use another account.

## What each role can do
- Owner: uploads files, gives read or edit access to named people, takes it
  back, and deletes their own documents.
- Viewer: sees only what was shared with them. With edit access they can also
  rename a document.
- Admin: sees the audit log, permission changes, alerts and users, and can
  switch a user off. The admin cannot open files.

## How permissions work
By default, nobody can open a document except its owner. The owner can give
another person "read" access (view and download) or "edit" access (also
rename). Only the owner can delete the document or share it.

The decision is made in one place: the function can_access in app/access.py.
Every route that touches a document calls it, so the server checks the rule on
every request. Hiding a button on the page is only for looks. If there is no
permission row for a person, they are refused.

When the owner removes someone, that person's permission row is deleted. Nothing
is saved in advance, so their next request is refused. A forbidden document and
a document that doesn't exist give the same "not found" answer, so nobody can
tell which documents are real. Every refusal is saved in the audit log.

## The audit log
Each row stores the hash of the row before it, so changing an old row breaks the
chain. The admin page can check this. The database also refuses updates and
deletes on that table.

## Run it on your machine
You need Python 3.13 and a PostgreSQL database (I used Neon).

    git clone https://github.com/shaikvaneesha11/TrustVault.git
    cd TrustVault
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

Make a file called .env in the main folder:

    DATABASE_URL=your database connection string
    TEST_DATABASE_URL=a second, different database for tests
    COOKIE_SECURE=0

Then run these in order:

    python -m app.create_tables
    python -m app.db_rules
    python -m app.seed
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000. The API docs are at /docs.

Tests:

    python -m pytest -v

The tests only use TEST_DATABASE_URL and stop if it is the same as the main
database.

## Deploying
I use Render. Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Set only DATABASE_URL. Do not set COOKIE_SECURE. Then run the three setup
commands above once against the database.

## Who can call what
- Anyone: GET /, GET /health, GET /docs, POST /auth/register, POST /auth/login
- Any logged in user: POST /auth/logout, GET /auth/me, GET /documents (only
  documents they own or were given)
- Owner role: POST /documents
- Owner of that document: DELETE /documents/{id}, and GET, POST and DELETE under
  /documents/{id}/permissions
- Owner, or someone with read or edit access: GET /documents/{id}/download
- Owner, or someone with edit access: PATCH /documents/{id}
- Admin only: everything under /admin

## What I left out
I kept the project small so I could test the permissions properly. I did not
build:
- Folders and inherited access. Sharing a folder can expose more files than
  intended, and I wanted one simple rule I can explain.
- Document versions and recovery of deleted files. Deleting is permanent.
- Sharing with people outside the system. Everyone needs an account.
- AI suggestions for who should get access. I spent the time on security and
  tests instead.

## What is still weak
- Anyone can sign up as an owner. I left sign-up open so you can try the app.
- Someone can lock another person's login for 15 minutes with wrong passwords.
- A stolen login cookie works until logout or 8 hours.
- An owner can find out whether an email is registered.
- Someone with full control of the database could remove the audit protections.
- There is no general rate limit apart from login.
- I did not try a malicious document title by hand in a browser.
The full list, with what I did about each risk, is in THREATS.md.

## Other files
THREATS.md, PROMPTS.md, WRITEUP.md and the tests folder.