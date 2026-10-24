# TrustVault: short write-up

## What I built
TrustVault is a document sharing website. An owner uploads a file and chooses
who can read or edit it. Nobody else can open it. Every upload, download,
change, delete and permission change is saved in an audit log, and so are the
refused attempts. An admin can look at the log, see alerts, and switch users
off, but cannot open the files.

It uses Python with FastAPI, a PostgreSQL database on Neon, and a simple web
page. It is deployed on Render. There are more than 20 automated tests, and
they use a separate test database.

## What I left out, and why
I did not build folders, document versions, recovery of deleted files, sharing
with people outside the system, or AI suggestions for sharing. I would rather
hand in a smaller system whose permissions I can explain and test than a bigger
one with a hole in it.

## My permission model
Nobody can open a document unless they own it or the owner gave them access. The
access is either read (view and download) or edit (also rename). Only the owner
can delete a document or share it. One function, `can_access` in
`app/access.py`, makes this decision, and every route that touches a document
calls it. If there is no permission row, the answer is no.

When the owner takes access away, that row is deleted, so the person's next
request is refused straight away. A forbidden document and a document that does
not exist give the same "not found" answer, so nobody can guess which ones are
real. Logins use random tokens stored as hashes, so logging out or switching a
user off ends their session at once.

## The audit log
Each row stores the hash of the row before it, so changing an old row breaks the
chain, and the admin page can check it. The database also refuses updates and
deletes on that table. This does not stop someone who controls the whole
database. I say so in THREATS.md.

## How I used AI, and where it was wrong
I used Claude for most of the code and explanations, one step at a time. It was
wrong several times, and PROMPTS.md has the details. Examples: it gave me a
setup command that I pasted into the wrong place, it told me to create a test
configuration file that I never made so my tests ran on my real database, it
wrote a revoke route that logged "allowed" when nothing was removed, and it
wrote a logout test and a search test that could not fail. I also removed a
security check on purpose twice to see if my tests would notice. They did.

## What is unfinished or weak
- Anyone can sign up as an owner. I left it open so you can try the app.
- Someone can lock another person's login for 15 minutes with wrong passwords.
- A stolen login cookie works until logout or 8 hours.
- An owner can find out whether an email is registered.
- Someone with full database control could remove the audit protections.
- There is no general rate limit apart from login.
- I did not test a malicious document title by hand in a browser.
The full list is in THREATS.md.

## Where to look
Live site and demo logins are in README.md. The ways I think it could be broken
are in THREATS.md. My AI use is in PROMPTS.md. The tests are in the tests folder.