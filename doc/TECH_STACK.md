# Tech Stack — Multi-Doc Writer (Solar Docs Automation)

Everything in this stack is **free and open-source**. No paid libraries, no
paid hosting required, no API keys, no subscriptions.

## Core

| Tool | Cost | Purpose |
|---|---|---|
| **Python 3** | Free | Runs the whole automation |
| **docxtpl** | Free (open-source, BSD license) | Fills `{{ field_name }}` placeholders inside Word docs. Built on python-docx + Jinja2. This is the engine doing the actual document generation. |
| **Jinja2** | Free (open-source, BSD license) | Templating syntax (`{{ }}`) that docxtpl uses under the hood. Also supports loops/conditionals if you ever need repeating rows (e.g. multiple line items in a bill). |

Install:
```
pip install docxtpl --break-system-packages
```
(docxtpl pulls in Jinja2 and python-docx automatically — no separate install needed)

## Web form version

| Tool | Cost | Purpose |
|---|---|---|
| **Flask** | Free (open-source, BSD license) | Minimal Python web framework — serves the local form and handles the ZIP download |
| **HTML/CSS** | Free (built into every browser) | The form itself — plain HTML, no framework, no build step |

Install:
```
pip install flask --break-system-packages
```

Run:
```
python app.py
```
Then open `http://127.0.0.1:5000` in any browser. Runs entirely on your own
machine — no internet connection needed once installed, no data leaves your
computer.

## What's deliberately NOT used (and why you don't need to pay for anything)

| Skipped | Why |
|---|---|
| Database | Every generation is stateless — JSON in, docx out. Nothing to store. |
| Cloud hosting | Runs locally on `127.0.0.1`. No server costs. |
| JavaScript framework (React, Vue, etc.) | A 19-field form doesn't need one — plain HTML does the job with zero build tooling. |
| Paid document APIs (e.g. paid mail-merge SaaS tools) | docxtpl does the same job for free, running entirely on your machine. |
| Node.js / npm | Not needed — this is pure Python end to end. |

## Optional future additions (still free, if you extend this later)

| Need | Free tool |
|---|---|
| Access the form from your phone/other devices on your home network | No new tool — just run Flask with `host="0.0.0.0"` instead of `127.0.0.1` |
| Generate Excel files too | `openpyxl` (free) |
| Generate/fill PDF files too | `pypdf` or `reportlab` (free) |
| Always-on hosted version, not just local | Free tiers exist on Render / Railway / Fly.io, but this adds real complexity for what's currently a simple local script — only worth it if you outgrow running it on-demand |
| Nicer-looking form UI | Plain CSS or Tailwind (free, CDN-hosted, no build step) — no need for a JS framework |

## Bottom line
Total cost to build and run this: **$0**. Everything is pip-installable,
open-source, and runs on your own machine. The only "cost" is disk space
and Python itself, which is free.
