# Project Memory: Solar Docs Automation

## 🧠 Core System Design & Rationale

### 1. Engine & Templating
* **docxtpl**: Selected as the central engine for document generation. It acts as a bridge between `python-docx` and the `Jinja2` templating engine, allowing conditional blocks, variable interpolation, and loops directly inside native Word `.docx` documents.
* **Jinja2**: Standard syntax (`{{ variable }}`) is used inside the templates to map data.

### 2. XML-Level Template Modification Pattern
* **Problem**: DOCX files store text inside fragmented XML runs (`<w:r><w:t>...</w:t></w:r>`). Substring replacements on raw text often break the XML structure or fail to find variables that are split across multiple runs (e.g., `{{` and `variable` in separate runs).
* **Solution**: 
  1. Unzip the `.docx` file (`zipfile`).
  2. Locate the contiguous XML run elements matching the target hardcoded value or fragmented tag.
  3. Perform exact, full-element tag replacement (e.g., `<w:t>OLD</w:t>` → `<w:t>{{ variable }}</w:t>`) to keep tags intact.
  4. Re-zip the package.
  5. Run an XSD-schema validation to ensure layout and styles match.

### 3. Smart Default Fallbacks
* **Rationale**: To prevent breaking existing workflows when introducing new configurable subdivision inputs (`officer_designation`, `subdivision_address`, `consumer_residential_address_suffix`, `vendor_address_suffix`), we implemented fallback default dictionaries.
* **Mechanism**: If these variables are not provided in the CLI JSON input or are submitted as blank fields in the web form, the backend merges standard values for the Alibag subdivision.

---

## 🎨 UI/UX Design System

* **Theme**: Deep space slate-indigo dark mode with glassmorphic cards.
* **Design Philosophy**: High-end consumer feel with strict structural layout. Organized 23 fields into 6 groups to avoid overwhelming input forms.
* **User Micro-interactions**: Added a "Load Sample Data" action script to immediately demonstrate system capability with real data.
* **Responsiveness**: Engineered CSS grid configurations that auto-wrap for mobile devices (tablets and phones) to make field use easier.

---

## 📝 Document-to-Field Mapping Reference

* **Total fields**: 23 (19 general project fields, 4 subdivision customization fields).
* **Full Mapping Table**: Refer to the mapping table in the project [README.md](file:///E:/webstack/multi_doc_writer/README.md) for detailed descriptions, templates where each is used, and formatting notes.

---

## 💡 What We Learned & Best Practices

1. **Exact-Element Replacement over Substrings**: Bare substring replacements inside `document.xml` can inadvertently change matching numeric sequences or letters in metadata or formatting attributes, leading to corrupted docx structures. Always isolate the text run (`<w:t>`) for edits.
2. **Offline Privacy Guarantee**: Keeping the web form inside local Flask runs (`127.0.0.1`) ensures that sensitive consumer information (residential addresses, consumer numbers, mobile contacts) never leaves the host machine.
3. **Validation Automation**: Running static checks on rendered outputs before opening them is a crucial safety gate. The `verify_rendered.py` script validates output cleanliness programmatically.
