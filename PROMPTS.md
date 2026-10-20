# PROMPTS.md

## Entry 1 - 20 Oct 2026
- Asked: Step-by-step setup for a FastAPI project on Windows PowerShell.
- Produced: PowerShell commands that write files using @' ... '@ blocks.
- Wrong because: I pasted the block into a file instead of the terminal, so the file contained the literal text @' and Python gave a SyntaxError. The file also ended up in the venv folder instead of app.
- Fixed by: Deleted the wrong file and created app/main.py in the editor with plain code only. Commit: <add link>

## Entry 2 - 20 Oct 2026
- Asked: Save the installed libraries to requirements.txt.
- Produced: pip freeze > requirements.txt
- Wrong because: PowerShell saved the file in a different encoding (UTF-16), so GitHub and Render could not read it properly.
- Fixed by: Wrote requirements.txt by hand in VS Code as UTF-8. Commit: b129d04