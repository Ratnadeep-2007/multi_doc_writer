#!/usr/bin/env python3
"""
Local one-time-input form for the solar project documents.

Run:
    pip install flask docxtpl --break-system-packages
    python3 app.py
Then open http://127.0.0.1:5000 in your browser.
"""
import io
import re
import zipfile
from pathlib import Path

from flask import Flask, request, render_template_string, send_file
from docxtpl import DocxTemplate

app = Flask(__name__)
TEMPLATE_DIR = Path(__file__).parent / "templates"

TEMPLATES = [
    "Commissioning_Report_TEMPLATE.docx",
    "Proforma_A_TEMPLATE.docx",
    "Guarantee_Certificate_TEMPLATE.docx",
    "Annexure3_TEMPLATE.docx",
    "Annex2_TEMPLATE.docx",
    "WorkCompletionReport_TEMPLATE.docx",
    "MeterTestingLetter_TEMPLATE.docx",
]


def dedupe_docx_bytes(data: bytes) -> bytes:
    """Fix a docxtpl quirk (seen with MeterTestingLetter_TEMPLATE.docx,
    which started life as a legacy .doc file) where saved docx files can
    contain duplicate zip entries, corrupting the file for some readers.
    No-op if there are no duplicates."""
    src = zipfile.ZipFile(io.BytesIO(data), "r")
    last = {item.filename: item for item in src.infolist()}
    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zout:
        written = set()
        for item in src.infolist():
            if item.filename in written:
                continue
            written.add(item.filename)
            zout.writestr(last[item.filename], src.read(last[item.filename]))
    return out_buf.getvalue()

# Group fields logically for the UI
GROUPS = [
    {
        "title": "Consumer General Info",
        "icon": "👤",
        "fields": [
            {"label": "Consumer Full Name", "name": "consumer_name", "ph": "SACHIN SAHDEV GAWAND", "required": True},
            {"label": "Consumer Number", "name": "consumer_number", "ph": "023130009549", "required": True},
            {"label": "Mobile Number", "name": "mobile_number", "ph": "9260557576", "required": True},
            {"label": "Email Address", "name": "email", "ph": "solar2ssitindia.com", "required": True},
        ]
    },
    {
        "title": "Address Information",
        "icon": "📍",
        "fields": [
            {"label": "Installation Address", "name": "install_address", "ph": "H. NO. 1098, TAL. ALIBAG PEN CIRCLE,", "required": True, "full_width": True},
            {"label": "Consumer Residential Address (Annex-2 only)", "name": "consumer_residential_address", "ph": "At Post Dhokawade", "required": True, "full_width": True},
            {"label": "Consumer Address Suffix (District/Taluka)", "name": "consumer_residential_address_suffix", "ph": "TAL. ALIBAG, DIST. RAIGAD", "required": False, "default": "TAL. ALIBAG, DIST. RAIGAD", "full_width": True},
        ]
    },
    {
        "title": "Solar System Specs",
        "icon": "☀️",
        "fields": [
            {"label": "Sanctioned Capacity (KW)", "name": "sanctioned_capacity_kw", "ph": "3.3", "required": True},
            {"label": "Rooftop Installed Capacity (KW)", "name": "rooftop_capacity_kw", "ph": "3", "required": True},
            {"label": "Sanction Number (with date)", "name": "sanction_number", "ph": "4138/ALIBAG-II/75755227 Date:17-Jul-2026", "required": True, "full_width": True},
            {"label": "PV Solar Panel Module Count", "name": "pv_module_count", "ph": "6", "required": True},
            {"label": "Solar Panel Module Wattage (W)", "name": "module_wattage", "ph": "550", "required": True},
            {"label": "Solar Panel Module Capacity (Watt, Auto-calculated)", "name": "module_capacity_watt", "ph": "3300", "required": False, "full_width": True},
            {"label": "Solar Panel Module Make / Manufacturer", "name": "module_make", "ph": "Waaree India pvt ltd", "required": True},
            {"label": "ALMM Model Number", "name": "almm_model_number", "ph": "AE14HXXXVHC10B", "required": True},
            {"label": "Inverter Capacity (KW)", "name": "inverter_capacity_kw", "ph": "3.3", "required": True},
            {"label": "Inverter Make / Manufacturer", "name": "inverter_make", "ph": "Polycab Solar Pvt. Ltd", "required": True},
            {"label": "Inverter Model / Rating", "name": "inverter_model", "ph": "Vs-502s", "required": True},
            {"label": "MPPT / Charge Controller Count", "name": "mppt_count", "ph": "1", "required": True},
            {"label": "Inverter Year of Manufacturing", "name": "inverter_manufacture_year", "ph": "2025", "required": True},
        ]
    },
    {
        "title": "Execution & Agreement Dates",
        "icon": "📅",
        "fields": [
            {"label": "Installation Date", "name": "installation_date", "ph": "4-June-2026", "required": True},
            {"label": "Agreement Date (DD/MM/YYYY)", "name": "agreement_date", "ph": "22/06/2026", "required": True},
            {"label": "Execution Date (Written out for Annex-2)", "name": "execution_date_text", "ph": "22nd of June 2026", "required": True, "full_width": True},
        ]
    },
    {
        "title": "Vendor Credentials",
        "icon": "🏢",
        "fields": [
            {"label": "Vendor Short Name", "name": "vendor_name", "ph": "S S Powertech", "required": True},
            {"label": "Vendor Full Name (with M/S)", "name": "vendor_name_full", "ph": "M/S S S PowerTech", "required": True},
            {"label": "Vendor Registered Address", "name": "vendor_address", "ph": "Ranjanpada, Post Awas, Tal. Alibag, District. Raigad 402201", "required": True, "full_width": True},
            {"label": "Vendor Address Suffix (Taluka/Dist/Pin)", "name": "vendor_address_suffix", "ph": "Tal: Alibag,  DIST. RAIGAD, 402201.", "required": False, "default": "Tal: Alibag,  DIST. RAIGAD, 402201.", "full_width": True},
        ]
    },
    {
        "title": "MSEDCL Subdivision (Optional)",
        "icon": "⚡",
        "fields": [
            {"label": "MSEDCL Officer Designation", "name": "officer_designation", "ph": "Deputy Executive Engineer Alibag II", "required": False, "default": "Deputy Executive Engineer Alibag II", "full_width": True},
            {"label": "Subdivision Registered Office Address", "name": "subdivision_address", "ph": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201", "required": False, "default": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201", "full_width": True},
        ]
    },
    {
        "title": "Meter Testing Letter",
        "icon": "🔌",
        "fields": [
            {"label": "Meter Serial Number", "name": "meter_serial_number", "ph": "U6541057", "required": True},
        ]
    }
]

FORM_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solar Docs Generator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary: #0b0f19;
    --bg-surface: rgba(22, 30, 49, 0.7);
    --border-color: rgba(255, 255, 255, 0.08);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --accent: #8b5cf6;
    --accent-hover: #a78bfa;
    --success: #10b981;
    --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  }
  
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  
  body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    background: radial-gradient(circle at 10% 20%, #1e1b4b 0%, #0f172a 50%, #020617 100%);
    background-attachment: fixed;
    color: var(--text-primary);
    min-height: 100vh;
    padding: 40px 20px;
    line-height: 1.5;
  }
  
  .container {
    max-width: 1000px;
    margin: 0 auto;
  }
  
  header {
    text-align: center;
    margin-bottom: 40px;
  }
  
  h1 {
    font-family: 'Outfit', sans-serif;
    font-size: 2.5rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 50%, #6366f1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }
  
  .subtitle {
    color: var(--text-secondary);
    font-size: 1.1rem;
    font-weight: 400;
  }
  
  .actions-bar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 24px;
    gap: 12px;
  }
  
  .btn-secondary {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
    padding: 10px 18px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: inherit;
  }
  
  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: var(--accent-hover);
    transform: translateY(-1px);
  }
  
  form {
    display: grid;
    grid-template-columns: 1fr;
    gap: 32px;
  }
  
  @media(min-width: 768px) {
    form {
      grid-template-columns: repeat(2, 1fr);
    }
    
    .full-width-section {
      grid-column: span 2;
    }
  }
  
  .card {
    background: var(--bg-surface);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 24px;
    box-shadow: var(--shadow);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  
  .card:hover {
    box-shadow: 0 12px 40px 0 rgba(139, 92, 246, 0.1);
  }
  
  .card-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 20px;
    color: var(--accent-hover);
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 12px;
  }
  
  .grid-fields {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  @media(min-width: 480px) {
    .grid-2 {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .field-wrapper {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .span-2 {
    grid-column: span 2;
  }
  
  label {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-primary);
  }
  
  .required-asterisk {
    color: #ef4444;
    margin-left: 2px;
  }
  
  input {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 12px;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.95rem;
    transition: all 0.2s ease;
    width: 100%;
  }
  
  input::placeholder {
    color: rgba(255, 255, 255, 0.25);
  }
  
  input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.25);
    background: rgba(15, 23, 42, 0.85);
  }
  
  .hint-text {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
  
  .submit-container {
    grid-column: 1 / -1;
    text-align: center;
    margin-top: 20px;
  }
  
  .btn-primary {
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    border: none;
    color: white;
    padding: 16px 40px;
    font-size: 1.1rem;
    font-weight: 600;
    border-radius: 12px;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
    transition: all 0.2s ease;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  
  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(139, 92, 246, 0.45);
    background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 50%, #4f46e5 100%);
  }
  
  .btn-primary:active {
    transform: translateY(0);
  }
  
  footer {
    text-align: center;
    margin-top: 60px;
    color: var(--text-secondary);
    font-size: 0.85rem;
  }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Solar Docs Auto-Fill</h1>
    <p class="subtitle">Fill the form once to generate all 5 solar project installation documents</p>
  </header>
  
  <div class="actions-bar">
    <button type="button" class="btn-secondary" onclick="fillSampleData()">⚡ Load Sachin Gawand Sample</button>
  </div>
  
  <form method="POST" action="/generate">
    {% for group in groups %}
      <div class="card {% if group.title in ['Solar System Specs', 'Address Information', 'MSEDCL Subdivision (Optional)'] %}full-width-section{% endif %}">
        <h2 class="card-title">{{ group.icon }} {{ group.title }}</h2>
        <div class="grid-fields {% if group.title in ['Consumer General Info', 'Solar System Specs', 'Execution & Agreement Dates'] %}grid-2{% endif %}">
          {% for field in group.fields %}
            <div class="field-wrapper {% if field.full_width %}span-2{% endif %}">
              <label for="{{ field.name }}">
                {{ field.label }}
                {% if field.required %}<span class="required-asterisk">*</span>{% endif %}
              </label>
              <input 
                type="text" 
                id="{{ field.name }}" 
                name="{{ field.name }}" 
                placeholder="{{ field.ph }}" 
                {% if field.default %}value="{{ field.default }}"{% endif %}
                {% if field.required %}required{% endif %}
              >
              <span class="hint-text">e.g. {{ field.ph }}</span>
            </div>
          {% endfor %}
        </div>
      </div>
    {% endfor %}
    
    <div class="submit-container">
      <button type="submit" class="btn-primary">
        📥 Generate & Download ZIP
      </button>
    </div>
  </form>
  
  <footer>
    <p>Stateless offline tool. No data is stored or transmitted. Powered by Python, Flask, and docxtpl.</p>
  </footer>
</div>

<script>
const sampleData = {
  "consumer_name": "SACHIN SAHDEV GAWAND",
  "consumer_number": "023130009549",
  "mobile_number": "9260557576",
  "email": "solar2ssitindia.com",
  "install_address": "H. NO. 1098, TAL. ALIBAG PEN CIRCLE,",
  "consumer_residential_address": "At Post Dhokawade",
  "consumer_residential_address_suffix": "TAL. ALIBAG, DIST. RAIGAD",
  "sanctioned_capacity_kw": "3.3",
  "rooftop_capacity_kw": "3",
  "module_make": "Waaree India pvt ltd",
  "inverter_capacity_kw": "3.3",
  "inverter_make": "Polycab Solar Pvt. Ltd",
  "pv_module_count": "6",
  "module_capacity_watt": "3300",
  "installation_date": "4-June-2026",
  "agreement_date": "22/06/2026",
  "execution_date_text": "22nd of June 2026",
  "vendor_name": "S S Powertech",
  "vendor_name_full": "M/S S S PowerTech",
  "vendor_address": "Ranjanpada, Post Awas, Tal. Alibag, District. Raigad 402201",
  "vendor_address_suffix": "Tal: Alibag,  DIST. RAIGAD, 402201.",
  "officer_designation": "Deputy Executive Engineer Alibag II",
  "subdivision_address": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201",
  "sanction_number": "4138/ALIBAG-II/75755227 Date:17-Jul-2026",
  "capacity_kw_compact": "3.3KW",
  "almm_model_number": "AE14HXXXVHC10B",
  "module_wattage": "550 WP",
  "total_capacity_kwp_note": "3.3KW (3300 / 1000 = 3.3)",
  "inverter_model": "Vs-502s",
  "mppt_count": "1",
  "inverter_manufacture_year": "2025",
  "meter_serial_number": "U6541057"
};

function fillSampleData() {
  for (const [key, value] of Object.entries(sampleData)) {
    const input = document.getElementById(key);
    if (input) {
      input.value = value;
    }
  }
  autoCalcModuleCapacity();
}

function autoCalcModuleCapacity() {
  const countInput = document.getElementById("pv_module_count");
  const wattInput = document.getElementById("module_wattage");
  const capacityInput = document.getElementById("module_capacity_watt");
  
  if (countInput && wattInput && capacityInput) {
    const count = parseInt(countInput.value) || 0;
    const wattMatch = wattInput.value.match(/\d+/);
    const watt = wattMatch ? parseInt(wattMatch[0]) : 0;
    if (count > 0 && watt > 0) {
      capacityInput.value = (count * watt).toString();
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const countInput = document.getElementById("pv_module_count");
  const wattInput = document.getElementById("module_wattage");
  if (countInput) countInput.addEventListener("input", autoCalcModuleCapacity);
  if (wattInput) wattInput.addEventListener("input", autoCalcModuleCapacity);
});
</script>
</body>
</html>
"""


def safe_folder_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())


@app.route("/")
def index():
    return render_template_string(FORM_HTML, groups=GROUPS)


@app.route("/generate", methods=["POST"])
def generate():
    data = {}
    for group in GROUPS:
        for field in group["fields"]:
            name = field["name"]
            val = request.form.get(name, "").strip()
            
            # If optional/has default and submitted empty, use its default
            if not val and "default" in field:
                val = field["default"]
                
            data[name] = val

    # Auto-calculate module_capacity_watt from panel count * panel wattage
    if data.get("pv_module_count") and data.get("module_wattage"):
        try:
            count = int(data["pv_module_count"])
            watt_match = re.search(r"\d+", str(data["module_wattage"]))
            if watt_match and count > 0:
                watt_val = int(watt_match.group(0))
                data["module_capacity_watt"] = str(count * watt_val)
                # Clean module_wattage to only be the number, so the template appends WP
                data["module_wattage"] = str(watt_val)
        except Exception:
            pass

    # Validate that required fields are not empty
    missing = []
    for group in GROUPS:
        for field in group["fields"]:
            if field.get("required") and not data.get(field["name"]):
                missing.append(field["label"])

    if missing:
        return f"Missing required fields: {', '.join(missing)}", 400

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for template_name in TEMPLATES:
            doc = DocxTemplate(TEMPLATE_DIR / template_name)
            doc.render(data)
            buf = io.BytesIO()
            doc.save(buf)
            fixed_bytes = dedupe_docx_bytes(buf.getvalue())
            out_name = template_name.replace("_TEMPLATE", "")
            zf.writestr(out_name, fixed_bytes)

    mem_zip.seek(0)
    folder = safe_folder_name(data["consumer_name"]) or "documents"
    return send_file(
        mem_zip,
        as_attachment=True,
        download_name=f"{folder}_documents.zip",
        mimetype="application/zip",
    )


if __name__ == "__main__":
    import sys
    # Support custom port/host if user wants, e.g. for access on local network
    host = "0.0.0.0" if "--network" in sys.argv else "127.0.0.1"
    print(f"Starting server on {host} port 5000...")
    app.run(debug=True, host=host, port=5000)
