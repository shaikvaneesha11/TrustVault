## How permissions work
By default, nobody can open a document except its owner. The owner can give
another person "read" access (they can view and download) or "edit" access
(they can also rename it). Only the owner can delete the document or share it.

The decision is made in one place: the function `can_access` in
`app/access.py`. Every route that touches a document calls it, so the server
checks the rule on every request. Hiding a button on the page is only for
looks. If there is no permission row for a person, they are refused.

When the owner removes someone, that person's permission row is deleted. Nothing
is saved in advance, so their very next request is refused. If a refused person
asks for a document, they get the same "not found" answer as for a document that
doesn't exist, so they can't tell which documents are real. Every refusal is
saved in the audit log.

The admin can see the activity log and manage users, but cannot open the files.

## What I left out
I kept the project small so I could test the permissions properly. I did not
build:
- Folders and inherited access. Sharing a folder can accidentally expose more
  files than intended, and I wanted one simple rule that I can explain.
- Document versions and recovery of deleted files. Deleting is permanent.
- Sharing with people outside the system. Everyone needs an account.
- AI suggestions for who should get access. I preferred to spend the time on
  security and tests.

## What is still weak
- Anyone can sign up as an owner. I left sign-up open so you can try the app.
- Someone can lock another person's login for 15 minutes by entering wrong
  passwords on purpose. It unlocks by itself.
- A stolen login cookie works until the person logs out or 8 hours pass.
- An owner can find out whether an email is registered, because sharing gives a
  different answer for unknown emails.
- Someone with full control of the database could remove the protections on the
  audit log. A separate database user that can only add rows would fix this, but
  I did not set it up.
- There is no general rate limit apart from login.
- I did not try a malicious document title by hand in the browser. The page
  shows text safely by design, and this is not checked in a browser yet.
More details are in THREATS.md.