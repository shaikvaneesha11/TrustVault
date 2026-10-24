# THREATS.md

These are the ways I think TrustVault can be broken, what I did about each,
and what I knowingly left open. Where it says "test", there is an automated test
in the tests folder. Where it says "by hand", I tried it myself in the browser.

## 1. Guessing other people's documents
Every document has a number in its URL, so the obvious attack is to log in as
a stranger and try other numbers. Every route that touches a document goes
through one function, get_allowed_doc, which calls can_access. If the document
is missing or you aren't allowed, you get the same 404 either way, so nobody can
tell which numbers exist. The refusal goes in the audit log.
Tests: a stranger downloading, and a real forbidden id versus a made-up id.

## 2. What happens if an access check is removed
I took out the "no grant means no access" line in access.py on purpose to see
if my tests would notice. 3 tests failed and 5 still passed. The ones that
still passed don't depend on that line, and the document list has a second
filter in the query itself. I put the line back afterwards.

## 3. Read and edit people doing more than they were given
Someone with read access should not be able to rename, delete or share.
Someone with edit access can rename but not delete or share. Only the owner
can delete or share. This is decided inside can_access.
Tests: both cases.

## 4. Taking access away
Nothing is handed out in advance. Each download checks the permissions table at
that moment, and revoking deletes the row, so the next request is refused.
Test: viewer downloads fine, owner revokes, the next download is refused.

## 5. Stolen, fake or old cookies
Sessions are stored in the database as hashes. A made-up cookie matches
nothing. Logging out deletes the row. When an admin deactivates someone, their
sessions are deleted at the same time, and is_active is also checked on every
request.
Tests: forged cookie, an old cookie replayed after logout, and a user switched
off while logged in.

## 6. Password guessing
After 5 wrong passwords for an email within 15 minutes the server returns 429,
even if the right password is used next. A wrong password and an unknown email
give the same message, and the slow password check runs for both. Passwords are
hashed with argon2. I also changed the limit to 999 once to make sure the
lockout test fails without it (1 failed, 6 passed). I did not measure response
times.

## 7. Normal users using admin routes
Admin routes need the admin role and give 403 to everyone else, 401 if not
logged in. The admin is also not allowed to download file contents, because
can_access gives admins nothing special.
Tests: every admin route for non-admins (the read routes, and the activate and
deactivate buttons), and an admin trying to download a document.

## 8. Bad uploads
The file type is decided from the content (PDF header or valid UTF-8 text), not
the extension. Files over 5 MB and empty files are refused, and filenames are
cut down to the last part with strange characters replaced.
Tests: fake PDF, oversize, empty, and a filename like ../../evil.txt.

## 9. Changing the audit log
Each row stores the hash of the row before it, so editing one breaks the chain,
and /admin/verify-chain shows where. The database also has triggers that refuse
update, delete and truncate on that table. When I first wrote the test for the
triggers it failed with "DID NOT RAISE" because I had never created
tests/conftest.py, so the tests were running against my real database and not
the test one. I created the file and separated the two databases.
Tests: updates, deletes and truncates are refused, and the chain stays valid.

## 10. Search showing things it shouldn't
The list only selects documents the user owns or was given, and each result is
also checked with can_access.
Test: a stranger searching by name, %, owner and empty category sees nothing of
the owner's, while the owner finds the document.

## 11. Script in a document title
The page builds everything from text nodes, never from HTML strings, and there
is a Content-Security-Policy that blocks inline script. A test checks the
header. I did not try a hostile title (like <img src=x onerror=alert(1)>) by
hand, so that part rests on how the page is built and has not been checked in
a browser.

## 12. Other sites sending requests for the user
The cookie is SameSite=Lax, and the server rejects any write (POST, PATCH,
DELETE) whose Origin header isn't its own host.
Tests: a write with a foreign Origin gets 403, and a normal same-site write
still works.

## 13. My site inside someone else's page
X-Frame-Options is DENY and the page CSP has frame-ancestors 'none', so
browsers refuse to show it in a frame.
Test: the page sends both headers.

## 14. Hidden buttons
The page hides buttons you can't use, but that is only for tidiness. The server
checks every request again, so calling the API directly (through /docs, curl or
a script) gets the same refusal.

## 15. Things I know are weak and left alone
- Someone can lock another person out for 15 minutes by failing their login on
  purpose. It clears by itself. The limit is per email, not per IP.
- When an owner shares with an email, the answer differs (404 or 200), so an
  owner can find out whether an email is registered.
- Anyone can register as an owner. I left sign-up open for the judges.
- A stolen cookie works until logout or 8 hours. I did not add device binding
  or short-lived tokens. Logging out, or an admin deactivating the account,
  kills it immediately.
- Upload and its audit row are two steps. A crash between them could miss a row.
- Someone who controls the database could drop the audit triggers. A separate
  insert-only database user would fix that, and I did not set it up.
- Someone with full database access could also rewrite the whole chain or
  delete the newest rows without the chain noticing.
- There is no rate limit outside login, and the whole upload is received before
  my 5 MB check runs.
- If access is revoked while a page is open, Download shows a JSON error. No
  file content leaks, because the server checks every download.