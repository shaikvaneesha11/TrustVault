# THREATS.md

How I think TrustVault could be broken, what I did about it, and what I
knowingly left open. "Tested" means there is an automated test or I tried it by hand.

# 1. Script injection through a document title
Attack: Someone uploads a document with a title like `<img src=x onerror=alert(1)>`.
If the page printed titles as HTML, that script would run in the viewer's browser
and could act as them.
What I did:The page never inserts server text as HTML. It builds every screen
with text nodes, so a title is only ever shown as plain text. I also added a
Content-Security-Policy that blocks inline scripts, so a mistake in one place
would still not run injected code.
Status: The CSP header is covered by an automated test. I have NOT yet tried a
hostile title by hand. I will upload one before submitting and update this line.

# 2. Cross-site request forgery
Attack: A different website tricks a logged-in user's browser into sending a
request to TrustVault, for example a delete or a share.
What I did: The session cookie is SameSite=Lax. On top of that, the server
rejects any write request (POST, PATCH, DELETE) whose Origin header is not my own host.
Status: Tested. One test sends a write with a foreign Origin and expects 403.
Another confirms a normal same-site request still works.

# 3. Clickjacking (my site shown inside a hostile page)
Attack:An attacker puts TrustVault in an invisible frame and tricks the user
into clicking a button, such as Delete or Grant.
What I did: Every response sends X-Frame-Options: DENY, and the main page also
sends frame-ancestors 'none' in its CSP, so browsers refuse to frame it.
Status: The headers are set in code. I have not written a test for this yet.

# 4. Hidden buttons are not security
Attack: A user lacks the Share or Delete button, but calls the API directly
(through /docs, curl or a script).
What I did: The page hides buttons only to keep the screen tidy. Every route
checks permission on the server through one function, can_access, and refuses
the request there. A missing document and a forbidden one both return 404, and
the refusal goes into the audit log.
Status: Tested. My tests call the routes directly as a stranger, as a
read-only user, and as a viewer, and expect refusals. I also removed the check
on purpose once, and tests failed, so they do test it.

# 5. Things I knowingly accepted
- A stolen session cookie works until logout or expiry (8 hours). Anyone who
  steals it from a user's browser can act as that user until then. I kept it simple
  and did not add device binding or short-lived tokens. A user logging out, or an
  admin deactivating the account, kills it immediately.
- A revoked person's open page can show raw JSON. If access is taken away
  while their list is open, clicking Download shows an error response instead of a
  friendly message. No file content is leaked, because the server checks every
  download. It is only untidy.