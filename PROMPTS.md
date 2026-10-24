# PROMPTS.md

I used Claude for most of this project. I gave it one step at a time and pasted
back the exact errors. Below are the times it got something wrong and what I
did about it. Entries 3 to 6 are about access control or the audit log.

## Entry 1 - 20 Oct 2026
Asked: How to set up a FastAPI project on Windows PowerShell.
It gave me: Commands that write files by pasting text between @' and '@.
What was wrong: I pasted that text into a file instead of running it in the
terminal. The file had a literal @' on line 1 and Python gave a SyntaxError. The
file was also in the venv folder, not in app.
What I did: Deleted it and made app/main.py in the editor with plain code.
Commit: https://github.com/shaikvaneesha11/TrustVault/commit/f15f0c0

## Entry 2 - 20 Oct 2026
Asked: How to save my installed libraries.
It gave me: `pip freeze > requirements.txt`.
What was wrong: PowerShell saved the file in the wrong encoding. GitHub could
not show it properly and Render would not have been able to build from it.
What I did: Wrote requirements.txt by hand in VS Code, saved as UTF-8.
Commit: https://github.com/shaikvaneesha11/TrustVault/commit/b129d04

## Entry 3 (audit log) - 21 Oct 2026
Asked: A test showing the audit log can't be changed, plus database triggers.
It gave me: The triggers, the test, and a conftest.py to point tests at a
separate database.
What was wrong: I never created conftest.py, so my tests were running
against my real database. The test failed with "DID NOT RAISE", and the failed
run had changed a real audit row. When I printed the two database hosts, my
main and "test" setup were not separate.
What I did: Created conftest.py, made a second Neon database for tests,
cleaned the main one, then installed the triggers on it.
Commit: https://github.com/shaikvaneesha11/TrustVault/commit/1fc07b9

## Entry 4 (audit log and access) - 22 Oct 2026
Asked: Routes for granting and revoking access, with audit logging.
It gave me: A revoke route that always wrote "allowed" to the audit log.
What was wrong: If the person had no access to begin with, nothing was
removed, but the log still said a revoke was allowed. The log was recording
something that did not happen.
What I did: It now logs "allowed" only when a grant was really deleted, and
"noop" otherwise. I added a test for it.
Commit: https://github.com/shaikvaneesha11/TrustVault/commit/31acd18

## Entry 5 (access tests) - 24 Oct 2026
Asked: Tests that one user can't reach another user's documents.
It gave me: A logout test and a search test that looked fine.
What was wrong: The logout test used the same client, which deletes its own
cookie after logout, so it would pass even if the server kept the session. The
search test only checked that a stranger saw nothing, so it would pass even if
search returned nothing for everyone.
**What I did:** The logout test now replays the old cookie from a new client.
The search test also checks that the owner finds the document.
Commit: https://github.com/shaikvaneesha11/TrustVault/commit/e94a8a7
## Entry 6 (access control, I broke it on purpose) - 21 and 22 Oct 2026
What I did: To see if my tests really test anything, I changed the "no
grant means no access" line in access.py so it let people in. 3 tests failed
and 5 still passed. The 5 don't depend on that line, and the document list
filters a second time in the query. I put the line back. Later I set the login
lockout limit to 999, 1 test failed and 6 passed, and I put that back too.
Commit: none, I did not commit the broken versions.

## What I reused across the week
- "Give me one step at a time and tell me where to paste it."
- "Explain each line so I can say it back to an interviewer."
- "Ask me questions after each part."
- When something failed I pasted the exact error and said which step I was on.