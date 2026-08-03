# Tools Required — Multi-Doc Writer

Everything here is free. This covers what you need *installed on your machine*
to run and edit this project (separate from the Python libraries listed in
`TECH_STACK.md`).

## Required

| Tool | Cost | Purpose | Get it |
|---|---|---|---|
| **Python 3** (3.9+) | Free | Runs the scripts and the Flask app | python.org/downloads — on Windows, check "Add Python to PATH" during install |
| **pip** | Free (comes with Python) | Installs the libraries (docxtpl, flask) | Included with Python automatically |
| **A terminal** | Free (built-in) | To run `python app.py`, `pip install`, etc. | Windows: Command Prompt or PowerShell (both pre-installed). No need to install anything extra. |
| **A web browser** | Free (built-in) | To use the form (`app.py`) and view/verify generated docs | Chrome, Edge, Firefox — whatever you already have |
| **Microsoft Word** or a free alternative | Free alternative available | To open/check the generated `.docx` files | Word if you have it, otherwise **LibreOffice Writer** (100% free, opens/edits .docx fine) — libreoffice.org |

## Recommended (makes editing/extending easier, still free)

| Tool | Cost | Purpose | Get it |
|---|---|---|---|
| **VS Code** | Free | Code editor — for editing `app.py`, `generate_docs.py`, the templates' field names, etc. | code.visualstudio.com |
| **VS Code Python extension** | Free | Syntax highlighting, autocomplete, run-in-editor for Python | Install from inside VS Code's Extensions tab |

## Optional (only if you extend this later)

| Tool | Cost | When you'd need it |
|---|---|---|
| **Git** | Free | If you want version history / to back this up to GitHub as you make changes | git-scm.com |
| **GitHub account** (free tier) | Free | Cloud backup / sharing the code, not required to just run it locally | github.com |
| **Postman** | Free tier | Only if you turn this into an API other software calls into — not needed for the current form-based version | postman.com |

## What you do NOT need
- No paid IDE (VS Code covers everything for free)
- No paid Word license required — LibreOffice opens `.docx` fine for checking output
- No cloud account, no AWS/Azure/GCP — this runs entirely on your own Windows machine
- No Docker, no containers — plain Python is enough for this size of project

## Quick setup checklist (Windows, from scratch)
1. Install Python from python.org, tick "Add Python to PATH"
2. Open Command Prompt, verify: `python --version`
3. `cd E:\webstack\multi_doc_writer`
4. `pip install docxtpl flask --break-system-packages`
5. Run either:
   - `python generate_docs.py sample_input.json` (CLI)
   - `python app.py` then open `http://127.0.0.1:5001` (web form)
6. Open generated `.docx` files in Word or LibreOffice to check them
