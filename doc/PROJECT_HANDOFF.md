# Solar Docs Auto-Fill Project — Handoff Notes

## What this project does
One-time input of a shared field set (consumer name, capacity, dates, etc.)
auto-fills 5 separate Word documents used for a rooftop solar / net-metering
installation (MSEDCL, Maharashtra). Instead of retyping the same values into
5 different docs, you fill them once and get all 5 generated.

Two ways to run it are already built and tested:
1. **CLI script** (`generate_docs.py`) — reads a JSON file, outputs 5 filled `.docx`.
2. **Local web form** (`app.py`, Flask) — fill a form in the browser, download a ZIP
   of all 5 filled `.docx`.

Both were tested end-to-end and the rendered output was visually compared
against the original documents (converted to PDF/JPEG and checked) — layout,
tables, and formatting all match.

## Current file locations (in the sandbox, NOT yet delivered to the user)
All under `/home/claude/work/`:

```
work/
├── app.py                  # Flask app — the web form + zip download
├── generate_docs.py        # CLI script — JSON in, 5 docx out
├── sample_input.json       # Example filled input (Gawand consumer data)
├── templates/              # THE ACTUAL TEMPLATES — docx with {{ jinja }} placeholders
│   ├── Commissioning_Report_TEMPLATE.docx
│   ├── Proforma_A_TEMPLATE.docx
│   ├── Guarantee_Certificate_TEMPLATE.docx
│   ├── Annexure3_TEMPLATE.docx
│   └── Annex2_TEMPLATE.docx
├── <5 original .docx files>          # untouched originals, kept for reference
└── unpacked_*/                       # scratch dirs from templating process, safe to delete
```

**Outstanding task from last session:** these files were supposed to be copied
to `/home/claude/deliverable/` and then to `/mnt/user-data/outputs/` via
`present_files` so the user can download them — that step got interrupted
(a `pkill` command hit the tool's execution time limit mid-batch) and was
never completed. **This is the immediate next step.**

## Field mapping (the "one-time input" schema)
These are ALL the fields used across the 5 templates, exactly as named in the
Jinja placeholders (`{{ field_name }}`). This is the single source of truth —
use these exact names in any JSON or form:

| Field name | Example value | Used in |
|---|---|---|
| `consumer_name` | SACHIN SAHDEV GAWAND | all 5 docs |
| `consumer_number` | 023130009549 | Commissioning Report, Annexure3, Annex2 |
| `mobile_number` | 9260557576 | Commissioning Report |
| `email` | solar2ssitindia.com | Commissioning Report |
| `install_address` | H. NO. 1098, TAL. ALIBAG PEN CIRCLE, | Commissioning Report, Proforma A, Annexure3, Annex2 |
| `consumer_residential_address` | At Post Dhokawade | Annex2 only (signature block address — can differ from install address) |
| `sanctioned_capacity_kw` | 3.3 | Commissioning Report, Proforma A, Annexure3 |
| `rooftop_capacity_kw` | 3 | Commissioning Report |
| `module_make` | Waaree India pvt ltd | Commissioning Report |
| `inverter_capacity_kw` | 3.3 | Commissioning Report |
| `inverter_make` | Polycab Solar Pvt. Ltd | Commissioning Report |
| `pv_module_count` | 6 | Commissioning Report |
| `module_capacity_kw` | 3.3 | Commissioning Report |
| `installation_date` | 4-June-2026 | Commissioning Report, Proforma A |
| `agreement_date` | 22/06/2026 | Annexure3, Annex2 |
| `execution_date_text` | 22nd of June 2026 | Annex2 (written-out date, see note below) |
| `vendor_name` | S S Powertech | Proforma A |
| `vendor_name_full` | M/S S S PowerTech | Proforma A, Annex2 |
| `vendor_address` | Ranjanpada, Post Awas, Tal. Alibag, District. Raigad 402201 | Annex2 |

`sample_input.json` in the work dir has all of these filled in with real
example values (from the Gawand consumer docs the user uploaded) — use it as
a reference for format/style expected in each field.

## Known limitations / things NOT templated (left as fixed hardcoded text)
Flag these to the user if they haven't confirmed them already:
- **Annexure3**: MSEDCL officer designation ("Deputy Executive Engineer Alibag
  II") and the subdivision registered office address ("CHENDHARE, TAL-ALIBAG,
  DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201") are
  hardcoded, not variables. Assumption: these are constant for this vendor's
  service area. If the user serves multiple MSEDCL subdivisions, these need
  to become fields too.
- **Annex2**: the "TAL. ALIBAG, DIST. RAIGAD" fragment attached to the
  consumer's residential address block is also hardcoded (not merged into
  `consumer_residential_address`).
- **`execution_date_text`**: in the original Annex2 docx, the date had an
  ordinal superscript ("22^TH^ of June 2026" with "TH" in superscript
  formatting). This was collapsed into one plain-text field
  (`execution_date_text`) where the user types the full phrase including the
  ordinal suffix (e.g. "22nd of June 2026") — superscript formatting on the
  ordinal is lost. Minor cosmetic tradeoff, flagged to the user already.
- **Data discrepancy noticed but not resolved**: the user's own uploaded
  reference images (a *different* consumer, "Ashish Jayvant Rane") show the
  consumer number as 023121009641 in one doc and 023130903096 in another, for
  what should be the same consumer. Not fixed/assumed — just worth the user
  double-checking their source data has one consistent consumer number per
  person before bulk-generating.

## How the templating was done (if more docs need the same treatment)
1. Read `/mnt/skills/public/docx/SKILL.md` first (mandatory per skill rules).
2. Unzip the docx: `unzip -q file.docx -d unpacked_dir`
3. Merge fragmented XML runs so text is contiguous and findable:
   `python3 /mnt/skills/public/docx/scripts/merge_runs.py unpacked_dir/`
4. Inspect `unpacked_dir/word/document.xml`, find the exact `<w:t>...</w:t>`
   elements holding the values to templatize (`grep -o '<w:t[^>]*>[^<]*</w:t>' document.xml`).
5. Do **exact, full-element string replacement** (`<w:t>OLD</w:t>` →
   `<w:t>{{ field }}</w:t>`) — NOT bare substring replacement, which caused a
   bug earlier in this project (a "3" digit collided with an unrelated "3"
   elsewhere in the doc). Always match the whole `<w:t...>...</w:t>` tag.
6. Rezip: `cd unpacked_dir && zip -Xr ../NAME_TEMPLATE.docx . -x '.*'`
7. Validate against the original:
   `python3 /mnt/skills/public/docx/scripts/office/validate.py NAME_TEMPLATE.docx --original ORIGINAL.docx`
   — should report "All validations PASSED!" with matching paragraph counts.
8. Render with docxtpl and sample data, convert to PDF/JPEG, and visually
   compare against the original to catch anything the XSD validator wouldn't
   (e.g. semantic mismatches):
   ```
   python3 scripts/office/soffice.py --headless --convert-to pdf output.docx
   pdftoppm -jpeg -r 100 output.pdf page
   ```

## Immediate next steps for whoever picks this up
1. Copy `templates/`, `app.py`, `generate_docs.py`, `sample_input.json` to
   `/mnt/user-data/outputs/` (a clean folder, e.g. `solar-docs-automation/`).
2. Add a short `README.md` inside that folder covering: how to install deps
   (`pip install docxtpl flask --break-system-packages`), how to run the CLI
   (`python3 generate_docs.py your_input.json`), and how to run the web form
   (`python3 app.py` then open `http://127.0.0.1:5001`).
3. Call `present_files` so the user can download the folder/zip.
4. Confirm with the user whether the hardcoded fields listed above
   (MSEDCL officer/subdivision address, Annex2 district fragment) should
   actually be turned into input fields too.
