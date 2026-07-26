# Project Memory: Solar Docs Automation

## 🧠 Core System Design & Rationale

### 1. Engine & Templating
* **docxtpl**: Selected as the central engine for document generation. It acts as a bridge between `python-docx` and `Jinja2`, allowing conditional blocks, variable interpolation, and table rendering directly inside native Word `.docx` documents.
* **Jinja2**: Standard Jinja2 syntax (`{{ variable }}`) is used across all 7 templates.

### 2. Auto-Calculated Solar Panel Capacity
* **Rationale**: To eliminate manual calculation errors, Total Solar Panel Capacity in Watts (`module_capacity_watt`) is computed dynamically:
  $$\text{module\_capacity\_watt} = \text{pv\_module\_count} \times \text{module\_wattage}$$
* **Implementation**:
  * **Frontend**: Dynamic JS event listeners in [app.py](file:///R:/multi_doc_writer/app.py) auto-update the capacity input field as the user types panel count or panel wattage.
  * **Backend & CLI**: [generate_docs.py](file:///R:/multi_doc_writer/generate_docs.py) and [app.py](file:///R:/multi_doc_writer/app.py) calculate `module_capacity_watt` automatically prior to rendering templates.

### 3. XML-Level Highlight Removal & Formatting Preservation
* **Problem**: Converted template files (like `MeterTestingLetter_TEMPLATE.docx` and `WorkCompletionReport_TEMPLATE.docx`) contained `<w:highlight w:val="yellow"/>` tags that visually shaded output text in yellow.
* **Solution**:
  1. Inspected template `word/document.xml` files.
  2. Stripped all `<w:highlight.../>` XML nodes while preserving structural font, table, and paragraph XML tags.
  3. All 7 documents render cleanly without any yellow background shading (`highlight_count = 0`).

### 4. Deduplication of Legacy `.doc` Zip Entries
* **Quirk**: Legacy `.doc` files converted to `.docx` (e.g. `MeterTestingLetter_TEMPLATE.docx`) can cause `docxtpl` to produce duplicate zip entries (e.g., duplicate `docProps/core.xml`), corrupting files for readers like LibreOffice.
* **Fix**: Added `dedupe_docx()` in `generate_docs.py` and `dedupe_docx_bytes()` in `app.py` to ensure output `.docx` files contain unique zip entries.

### 5. Smart Default Fallbacks & Field Merging
* **Subdivision Fallbacks**: Optional MSEDCL subdivision inputs (`officer_designation`, `subdivision_address`, `consumer_residential_address_suffix`, `vendor_address_suffix`) fallback to Alibag subdivision defaults if omitted.
* **Redundant Field Removal**: Removed redundant fields `capacity_kw_compact` and `total_capacity_kwp_note`. Replaced with Jinja template expressions:
  * `{{ sanctioned_capacity_kw }}KW`
  * `{{ sanctioned_capacity_kw }}KW ({{ module_capacity_watt }} / 1000 = {{ sanctioned_capacity_kw }})`

---

## 🎨 UI/UX Design System

* **Theme**: Deep space slate-indigo dark mode with glassmorphic cards.
* **Consolidated Card Groups**: Form fields are organized into 5 logical groups:
  1. `Consumer General Info` (Name, Consumer #, Mobile, Email)
  2. `Address Information` (Install Address, Residential Address, Suffix)
  3. `Solar System Specs` (Consolidated hardware specs: Capacities, Sanction #, Panel Count, Panel Wattage, ALMM #, Inverter Make, Inverter Model / Rating, MPPT Count, Year of Mfg)
  4. `Execution & Agreement Dates` (Installation Date, Agreement Date, Execution Text)
  5. `Vendor Credentials` (Vendor Short/Full Name, Registered Address)
  6. `MSEDCL Subdivision (Optional)` (Officer Designation, Subdivision Address)
  7. `Meter Testing Letter` (Meter Serial #)

---

## 📝 Document-to-Field Mapping Summary

* **Total unique fields**: 30 non-redundant fields.
* **Full Mapping Table**: Refer to [README.md](file:///R:/multi_doc_writer/README.md) for full field descriptions and template usage.
