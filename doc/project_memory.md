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

### 6. Suffix, Unit Dropdowns & Smart Conversion
* **Goal**: Provide flexibility in unit selection next to capacities (`kW`, `W`) and module wattage (`WP`, `W`, `Wp`) inputs, while ensuring the engine receives clean numeric data and correct conversions.
* **Implementation**:
  * Added dynamic dropdown selectors to input fields in the UI.
  * In the backend and CLI (`app.py` and `generate_docs.py`), any user-typed trailing unit suffixes are stripped via regex.
  * If a capacity value is submitted in Watts (`W` or `w`) instead of Kilowatts (`kW`), the system automatically divides the value by `1000` to convert it to standard Kilowatts format (required by hardcoded net-metering layout formulas).

### 7. ZIP Archive Folder Nesting
* **Rationale**: To prevent extracted files from scattering and cluttering the user's local target directory upon extraction.
* **Implementation**:
  * Generated documents are placed inside a parent folder (named after the consumer, e.g. `SACHIN_SAHDEV_GAWAND/`) within the downloadable ZIP archive.

---

## 🎨 UI/UX Design System

* **Theme**: Flat utility style (Design Spec v2) featuring a clean light-grey page canvas (`#f7f8fa`), solid white card surfaces, a dark sidebar (`#14161f`), and a single focused indigo accent (`#4f46e5`).
* **Icons**: Swapped emojis for standard Lucide vector icons (`user`, `map-pin`, `sun`, `calendar`, `building-2`, `zap`, `plug`) rendered via CDN.
* **Density & Scan-ability**: Reduced card padding, card hover-lift animations, and text gradient decorations to focus strictly on paperwork efficiency.
* **Validation**: Small solid dot indicators in the sidebar turn green dynamically when a card's required fields are fully filled in.
* **Actions**: Includes outlines for loading sample data, a red outline clear button (with confirmation alerts) to wipe form states, and a streamlined loader spinner modal.
* **Mobile Responsiveness**: Designed a sliding sidebar drawer for screens `< 992px`, toggleable via a sticky top header bar and a backdrop blur overlay. The drawer auto-closes upon clicking navigation anchors to streamline document editing.

---

## 📝 Document-to-Field Mapping Summary

* **Total unique fields**: 30 non-redundant fields.
* **Full Mapping Table**: Refer to [README.md](file:///E:/webstack/Auto_Application_Deep/Auto_Application_Deep/multi_doc_writer/README.md) for full field descriptions and template usage.

---

## 🌐 Deployment & Name Configuration Memory

### 1. DNS Settings (Nameservers & Records)
* **Main Subdomain**: `autodocumentation.sspowertech.com`
* **WWW Subdomain**: `www.autodocumentation.sspowertech.com`
* **Hosting Server IP**: `190.92.174.87` (resolved from main domain `sspowertech.com` hosting)
* **DNS Resolution**: Both entries are configured as **A records** pointing to `190.92.174.87`. This resolves CNAME collision errors (such as `CNAME and other data` invalid zone errors) and ensures consistent routing for both `www` and non-`www` requests.

### 2. cPanel Hosting Environment
* **Application Root Directory**: `/home/<cpanel_user>/autodocumentation`
* **Application URL**: `autodocumentation.sspowertech.com`
* **WSGI Startup Script**: `passenger_wsgi.py` (imports the Flask `app` from `app.py` and exposes it as the global `application` object).
* **Virtualenv Dependency Loading**: The virtual environment's `site-packages` directory is configured to load via the `sys.path.insert()` helper block inside `passenger_wsgi.py` to ensure dependencies like `docxtpl` and `flask` load correctly under the Phusion Passenger daemon.
