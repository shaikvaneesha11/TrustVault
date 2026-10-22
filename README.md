# TrustVault

My submission for the Snovasys hiring challenge. It is a document sharing app
where a document can only be opened by people who were given access, and every
open, including the refused ones, is written to an audit log.

Live: https://trustvault-0wp7.onrender.com
(It is on a free plan, so the first load can take about a minute.)

## Demo logins
Password for all of them: Demo-Pass-2026

- Admin: admin@trustvault.demo
- Owner: owner@trustvault.demo
- Owner 2: owner2@trustvault.demo
- Viewer: viewer@trustvault.demo

## What the roles can do
- Owner: uploads files, gives read or edit access to named people, takes it back, deletes.
- Viewer: sees only what was shared with them. With edit access they can rename a file.
- Admin: sees the audit log, alerts and users, and can switch a user off. Cannot open files.

## How permissions work
**WRITE THIS YOURSELF.** Explain it the way you would to the interviewer.
Say who can reach a document, where the decision is made (`can_access` in
`app/access.py`), and what happens when the owner removes someone.

## Running it on your machine
You need Python 3.13 and a Postgres database (I used Neon).

    git clone https://github.com/shaikvaneesha11/TrustVault.git
    cd TrustVault
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

Make a `.env` file:

    DATABASE_URL=your database string
    TEST_DATABASE_URL=a second, separate database for tests
    COOKIE_SECURE=0

Then:

    python -m app.create_tables
    python -m app.db_rules
    python -m app.seed
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000. API docs are at /docs.

Tests: `python -m pytest -v`. They only use TEST_DATABASE_URL and stop if it is
the same as the main one.

## Deploying
Render, with build command `pip install -r requirements.txt` and start command
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set DATABASE_URL only. Then run
the three setup commands above once against the database.

## Who can call what
- Anyone: GET /, GET /health, POST /auth/register, POST /auth/login
- Any logged in user: /auth/logout, /auth/me, GET /documents (only their own or shared ones)
- Owner role: POST /documents
- Owner of that document: DELETE /documents/{id}, and everything under /documents/{id}/permissions
- Owner, or someone with read or edit access: GET /documents/{id}/download
- Owner, or someone with edit access: PATCH /documents/{id}
- Admin only: everything under /admin

## The audit log
Every row stores a hash of the row before it, so changing an old row breaks the
chain. /admin/verify-chain checks it. The database also refuses updates and
deletes on that table.

## What I left out
**WRITE THIS YOURSELF.** Folders, versions, sharing outside the system,
recovering deleted files and AI suggestions for sharing are not built. Say why
in your own words, for example that you preferred a smaller thing you can test.

## What is still weak
**WRITE THIS YOURSELF.** Be honest. Start from THREATS.md. For example: a stolen
cookie works until logout or 8 hours, anyone can register as an owner, and
someone with full database control could remove the audit triggers.

## Other files
THREATS.md, PROMPTS.md and the tests folder.