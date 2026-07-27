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
        "icon": "user",
        "fields": [
            {"label": "Consumer Full Name", "name": "consumer_name", "ph": "SACHIN SAHDEV GAWAND", "required": True},
            {"label": "Consumer Number", "name": "consumer_number", "ph": "023130009549", "required": True},
            {"label": "Mobile Number", "name": "mobile_number", "ph": "9260557576", "required": True},
            {"label": "Email Address", "name": "email", "ph": "solar2ssitindia.com", "required": True},
        ]
    },
    {
        "title": "Address Information",
        "icon": "map-pin",
        "fields": [
            {"label": "Installation Address", "name": "install_address", "ph": "H. NO. 1098, TAL. ALIBAG PEN CIRCLE,", "required": True, "full_width": True},
            {"label": "Consumer Residential Address (Annex-2 only)", "name": "consumer_residential_address", "ph": "At Post Dhokawade", "required": True, "full_width": True},
            {"label": "Consumer Address Suffix (District/Taluka)", "name": "consumer_residential_address_suffix", "ph": "TAL. ALIBAG, DIST. RAIGAD", "required": False, "default": "TAL. ALIBAG, DIST. RAIGAD", "full_width": True},
        ]
    },
    {
        "title": "Solar System Specs",
        "icon": "sun",
        "fields": [
            {"label": "Sanctioned Capacity", "name": "sanctioned_capacity_kw", "ph": "3.3", "required": True, "unit_choices": ["kW", "W"], "unit_default": "kW"},
            {"label": "Rooftop Installed Capacity", "name": "rooftop_capacity_kw", "ph": "3", "required": True, "unit_choices": ["kW", "W"], "unit_default": "kW"},
            {"label": "Sanction Number (with date)", "name": "sanction_number", "ph": "4138/ALIBAG-II/75755227 Date:17-Jul-2026", "required": True, "full_width": True},
            {"label": "PV Solar Panel Module Count", "name": "pv_module_count", "ph": "6", "required": True},
            {"label": "Solar Panel Module Wattage", "name": "module_wattage", "ph": "550", "required": True, "unit_choices": ["WP", "W", "Wp"], "unit_default": "WP"},
            {"label": "Solar Panel Module Capacity (Watt, Auto-calculated)", "name": "module_capacity_watt", "ph": "3300", "required": False, "full_width": True},
            {"label": "Solar Panel Module Make / Manufacturer", "name": "module_make", "ph": "Waaree India pvt ltd", "required": True},
            {"label": "ALMM Model Number", "name": "almm_model_number", "ph": "AE14HXXXVHC10B", "required": True},
            {"label": "Inverter Capacity", "name": "inverter_capacity_kw", "ph": "3.3", "required": True, "unit_choices": ["kW", "W"], "unit_default": "kW"},
            {"label": "Inverter Make / Manufacturer", "name": "inverter_make", "ph": "Polycab Solar Pvt. Ltd", "required": True},
            {"label": "Inverter Model / Rating", "name": "inverter_model", "ph": "Vs-502s", "required": True},
            {"label": "MPPT / Charge Controller Count", "name": "mppt_count", "ph": "1", "required": True},
            {"label": "Inverter Year of Manufacturing", "name": "inverter_manufacture_year", "ph": "2025", "required": True},
        ]
    },
    {
        "title": "Execution & Agreement Dates",
        "icon": "calendar",
        "fields": [
            {"label": "Installation Date", "name": "installation_date", "ph": "4-June-2026", "required": True},
            {"label": "Agreement Date (DD/MM/YYYY)", "name": "agreement_date", "ph": "22/06/2026", "required": True},
            {"label": "Execution Date (Written out for Annex-2)", "name": "execution_date_text", "ph": "22nd of June 2026", "required": True, "full_width": True},
        ]
    },
    {
        "title": "Vendor Credentials",
        "icon": "building-2",
        "fields": [
            {"label": "Vendor Short Name", "name": "vendor_name", "ph": "S S Powertech", "required": True},
            {"label": "Vendor Full Name (with M/S)", "name": "vendor_name_full", "ph": "M/S S S PowerTech", "required": True},
            {"label": "Vendor Registered Address", "name": "vendor_address", "ph": "Ranjanpada, Post Awas, Tal. Alibag, District. Raigad 402201", "required": True, "full_width": True},
            {"label": "Vendor Address Suffix (Taluka/Dist/Pin)", "name": "vendor_address_suffix", "ph": "Tal: Alibag,  DIST. RAIGAD, 402201.", "required": False, "default": "Tal: Alibag,  DIST. RAIGAD, 402201.", "full_width": True},
        ]
    },
    {
        "title": "MSEDCL Subdivision (Optional)",
        "icon": "zap",
        "fields": [
            {"label": "MSEDCL Officer Designation", "name": "officer_designation", "ph": "Deputy Executive Engineer Alibag II", "required": False, "default": "Deputy Executive Engineer Alibag II", "full_width": True},
            {"label": "Subdivision Registered Office Address", "name": "subdivision_address", "ph": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201", "required": False, "default": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201", "full_width": True},
        ]
    },
    {
        "title": "Meter Testing Letter",
        "icon": "plug",
        "fields": [
            {"label": "Meter Serial Number", "name": "meter_serial_number", "ph": "U6541057", "required": True},
        ]
    }
]

FORM_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solar Docs Generator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/lucide/dist/umd/lucide.min.js"></script>
<style>
  :root {
    --bg-page:        #f7f8fa;
    --bg-surface:      #ffffff;
    --bg-sidebar:      #14161f;
    --border:          #e2e4e9;
    --border-sidebar:  rgba(255,255,255,0.08);

    --text-primary:    #14161f;
    --text-secondary:  #6b7280;
    --text-on-dark:    #f4f5f7;
    --text-on-dark-secondary: #9497a5;

    --accent:          #4f46e5;
    --accent-hover:    #4338ca;
    --accent-soft:     #eef0fd;

    --success:         #16a34a;
    --danger:          #dc2626;

    --radius-sm: 6px;
    --radius-md: 10px;
    --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  }
  
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  
  body {
    font-family: var(--font-sans);
    background: var(--bg-page);
    color: var(--text-primary);
    min-height: 100vh;
    display: flex;
    overflow-x: hidden;
    line-height: 1.5;
  }

  .app-layout {
    display: flex;
    width: 100%;
    min-height: 100vh;
  }

  /* Sidebar Design */
  .sidebar {
    width: 280px;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border-sidebar);
    padding: 32px 20px;
    display: flex;
    flex-direction: column;
    position: fixed;
    height: 100vh;
    left: 0;
    top: 0;
    z-index: 100;
  }

  .sidebar-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 32px;
  }

  .logo-icon {
    font-size: 1.4rem;
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .logo-text {
    font-family: var(--font-sans);
    font-size: 1.25rem;
    font-weight: 750;
    letter-spacing: -0.3px;
    color: var(--text-on-dark);
  }

  .sidebar-progress {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-sidebar);
    border-radius: var(--radius-sm);
    padding: 12px;
    margin-bottom: 24px;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    font-size: 0.8rem;
  }

  .progress-label {
    color: var(--text-on-dark-secondary);
    font-weight: 500;
  }

  .progress-pct {
    font-weight: 600;
    color: var(--text-on-dark);
  }

  .progress-track {
    width: 100%;
    height: 4px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 2px;
    overflow: hidden;
  }

  .progress-bar {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.3s ease;
  }

  .sidebar-nav {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 24px;
  }

  .sidebar-nav ul {
    list-style: none;
  }

  .nav-item {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    margin-bottom: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
    color: var(--text-on-dark-secondary);
    border-left: 2px solid transparent;
  }

  .nav-item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-on-dark);
  }

  .nav-item.active {
    background: rgba(79, 70, 229, 0.12);
    border-left-color: var(--accent);
    color: var(--text-on-dark);
  }

  .nav-icon {
    display: inline-flex;
    align-items: center;
    margin-right: 10px;
    color: inherit;
  }
  
  .nav-icon svg {
    width: 16px;
    height: 16px;
  }

  .nav-title {
    font-size: 0.85rem;
    font-weight: 500;
  }

  .nav-status-badge {
    margin-left: auto;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: var(--text-on-dark-secondary);
    transition: background-color 0.2s ease;
  }

  .nav-status-badge.complete {
    background-color: var(--success);
  }

  .sidebar-footer {
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-top: 1px solid var(--border-sidebar);
    padding-top: 16px;
  }

  .btn-sample-load {
    background: transparent;
    border: 1px solid var(--accent);
    color: var(--accent);
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: inherit;
    text-align: center;
  }

  .btn-sample-load:hover {
    background: var(--accent-soft);
  }

  .btn-clear-data {
    background: transparent;
    border: 1px solid var(--danger);
    color: var(--danger);
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: inherit;
    text-align: center;
  }

  .btn-clear-data:hover {
    background: rgba(220, 38, 38, 0.05);
  }

  /* Main Content Layout */
  .main-content {
    margin-left: 280px;
    flex: 1;
    padding: 48px 48px;
    max-width: 840px;
    width: calc(100% - 280px);
  }

  .app-header {
    margin-bottom: 32px;
  }

  .app-header h1 {
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text-primary);
    margin-bottom: 6px;
  }

  .app-header .subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    font-weight: 400;
  }

  /* Form and Cards Styles */
  form {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 24px;
    transition: border-color 0.15s ease;
    scroll-margin-top: 24px;
  }

  .card:focus-within {
    border-color: var(--accent);
  }

  .card-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 20px;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
  }

  .card-title svg {
    width: 18px;
    height: 18px;
    color: var(--text-secondary);
  }

  .grid-fields {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .grid-2 {
    grid-template-columns: repeat(2, 1fr);
  }

  @media(max-width: 768px) {
    .grid-2 {
      grid-template-columns: 1fr;
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

  @media(max-width: 768px) {
    .span-2 {
      grid-column: span 1;
    }
  }

  .full-width-section {
    width: 100%;
  }

  label {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .required-asterisk {
    color: var(--danger);
    margin-left: 2px;
  }

  /* Form Elements Control */
  input, select {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.85rem;
    transition: all 0.15s ease;
  }

  input {
    width: 100%;
  }

  select {
    cursor: pointer;
    min-width: 80px;
  }

  option {
    background: var(--bg-surface);
    color: var(--text-primary);
  }

  input::placeholder {
    color: var(--text-secondary);
    opacity: 0.5;
  }

  input:focus, select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-soft);
  }

  .hint-text {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .submit-container {
    text-align: left;
    margin-top: 8px;
  }

  .btn-primary {
    background: var(--accent);
    border: 1px solid var(--accent);
    color: white;
    padding: 14px 28px;
    font-size: 0.85rem;
    font-weight: 600;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .btn-primary:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
  }

  .btn-primary:active {
    transform: none;
  }

  footer {
    text-align: left;
    margin-top: 48px;
    color: var(--text-secondary);
    font-size: 0.85rem;
    padding-bottom: 24px;
  }

  /* Loader Modal Overlay */
  .loader-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(20, 22, 31, 0.5);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
    transition: opacity 0.25s ease;
  }
  
  .loader-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 32px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    max-width: 340px;
    width: 90%;
  }
  
  .spinner {
    width: 48px;
    height: 48px;
    border: 3px solid var(--border);
    border-top: 3px solid var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
  }
  
  .loader-card h3 {
    font-size: 1.15rem;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--text-primary);
  }

  .loader-card p {
    color: var(--text-secondary);
    font-size: 0.85rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* Responsive styling */
  @media (max-width: 992px) {
    .app-layout {
      flex-direction: column;
    }
    
    .sidebar {
      width: 100%;
      height: auto;
      position: relative;
      border-right: none;
      border-bottom: 1px solid var(--border-sidebar);
      padding: 24px;
    }
    
    .main-content {
      margin-left: 0;
      width: 100%;
      padding: 32px 24px;
    }
    
    .app-header h1 {
      font-size: 1.5rem;
    }
  }
</style>
</head>
<body>
<div class="app-layout">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-logo">
      <span class="logo-icon"><i data-lucide="sun"></i></span>
      <span class="logo-text">Solar Docs</span>
    </div>
    
    <!-- Progress Indicator -->
    <div class="sidebar-progress">
      <div class="progress-info">
        <span class="progress-label">Form Progress</span>
        <span class="progress-pct" id="progress-pct">0%</span>
      </div>
      <div class="progress-track">
        <div class="progress-bar" id="progress-bar" style="width: 0%;"></div>
      </div>
    </div>
    
    <!-- Navigation list -->
    <nav class="sidebar-nav">
      <ul>
        {% for group in groups %}
          <li class="nav-item" data-section="{{ loop.index0 }}" onclick="scrollToSection('card-section-{{ loop.index0 }}')">
            <span class="nav-icon"><i data-lucide="{{ group.icon }}"></i></span>
            <span class="nav-title">{{ group.title }}</span>
            <span class="nav-status-badge" id="badge-{{ loop.index0 }}"></span>
          </li>
        {% endfor %}
      </ul>
    </nav>
    
    <!-- Quick Actions -->
    <div class="sidebar-footer">
      <button type="button" class="btn-sample-load" onclick="fillSampleData()">
        Load Sample Data
      </button>
      <button type="button" class="btn-clear-data" onclick="clearData()">
        Clear Form Data
      </button>
    </div>
  </aside>
  
  <!-- Main Contents -->
  <main class="main-content">
    <header class="app-header">
      <h1>Solar Docs Auto-Fill</h1>
      <p class="subtitle">Fill the form once to generate all 7 solar installation documents</p>
    </header>
    
    <form method="POST" action="/generate" id="docs-form">
      {% for group in groups %}
        <div class="card {% if group.title in ['Solar System Specs', 'Address Information', 'MSEDCL Subdivision (Optional)'] %}full-width-section{% endif %}" id="card-section-{{ loop.index0 }}">
          <h2 class="card-title"><i data-lucide="{{ group.icon }}"></i> {{ group.title }}</h2>
          <div class="grid-fields {% if group.title in ['Consumer General Info', 'Solar System Specs', 'Execution & Agreement Dates'] %}grid-2{% endif %}">
            {% for field in group.fields %}
              <div class="field-wrapper {% if field.full_width %}span-2{% endif %}">
                <label for="{{ field.name }}">
                  {{ field.label }}
                  {% if field.required %}<span class="required-asterisk">*</span>{% endif %}
                </label>
                {% if field.unit_choices %}
                  <div style="display: flex; gap: 8px; width: 100%; align-items: center;">
                    <input 
                      type="text" 
                      id="{{ field.name }}" 
                      name="{{ field.name }}" 
                      placeholder="{{ field.ph }}" 
                      {% if field.default %}value="{{ field.default }}"{% endif %}
                      {% if field.required %}required{% endif %}
                      style="flex: 1;"
                    >
                    <input type="hidden" name="{{ field.name }}_unit" value="{{ field.unit_default }}">
                    <span class="field-unit-label" style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); min-width: 24px; text-align: left;">{{ field.unit_default }}</span>
                  </div>
                {% else %}
                  <input 
                    type="text" 
                    id="{{ field.name }}" 
                    name="{{ field.name }}" 
                    placeholder="{{ field.ph }}" 
                    {% if field.default %}value="{{ field.default }}"{% endif %}
                    {% if field.required %}required{% endif %}
                  >
                {% endif %}
                <span class="hint-text">e.g. {{ field.ph }}</span>
              </div>
            {% endfor %}
          </div>
        </div>
      {% endfor %}
      
      <div class="submit-container">
        <button type="submit" class="btn-primary">
          Generate & Download ZIP
        </button>
      </div>
    </form>
    
    <footer>
      <p>Stateless offline tool. No data is stored or transmitted. Powered by Python, Flask, and docxtpl.</p>
    </footer>
  </main>
</div>

<!-- Loader Modal Overlay -->
<div id="loader-overlay" class="loader-overlay" style="display: none; opacity: 0;">
  <div class="loader-card">
    <div class="spinner"></div>
    <h3>Generating Solar Docs</h3>
    <p id="loader-text">Preparing documents...</p>
  </div>
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
  "sanctioned_capacity_kw_unit": "kW",
  "rooftop_capacity_kw": "3",
  "rooftop_capacity_kw_unit": "kW",
  "module_make": "Waaree India pvt ltd",
  "inverter_capacity_kw": "3.3",
  "inverter_capacity_kw_unit": "kW",
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
  "module_wattage": "550",
  "module_wattage_unit": "WP",
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
  updateProgress();
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

// Clear Data function
function clearData() {
  if (confirm("Are you sure you want to clear all form fields?")) {
    const inputs = document.querySelectorAll('#docs-form input[type="text"]');
    inputs.forEach(input => {
      input.value = "";
    });
    updateProgress();
  }
}

// Sidebar Scroll Function
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// Progress and Status calculation
function updateProgress() {
  const groups = {{ groups|tojson }};
  let totalRequired = 0;
  let filledRequired = 0;
  
  groups.forEach((group, idx) => {
    let groupFilled = true;
    let groupRequiredCount = 0;
    
    group.fields.forEach(field => {
      if (field.required) {
        groupRequiredCount++;
        totalRequired++;
        
        const input = document.getElementById(field.name);
        if (input && input.value.trim() !== "") {
          filledRequired++;
        } else {
          groupFilled = false;
        }
      }
    });
    
    // Update badge in sidebar
    const badge = document.getElementById(`badge-${idx}`);
    if (badge) {
      if (groupRequiredCount === 0 || groupFilled) {
        badge.className = "nav-status-badge complete";
      } else {
        badge.className = "nav-status-badge";
      }
    }
  });
  
  const pct = totalRequired > 0 ? Math.round((filledRequired / totalRequired) * 100) : 0;
  document.getElementById('progress-pct').innerText = `${pct}%`;
  document.getElementById('progress-bar').style.width = `${pct}%`;
}

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Lucide icons
  lucide.createIcons();

  const countInput = document.getElementById("pv_module_count");
  const wattInput = document.getElementById("module_wattage");
  if (countInput) countInput.addEventListener("input", autoCalcModuleCapacity);
  if (wattInput) wattInput.addEventListener("input", autoCalcModuleCapacity);
  
  // Track input to update progress
  const inputs = document.querySelectorAll('input');
  inputs.forEach(input => {
    input.addEventListener('input', updateProgress);
    input.addEventListener('change', updateProgress);
  });
  
  updateProgress();

  // Scroll active section highlighter using IntersectionObserver
  const observerOptions = {
    root: null,
    rootMargin: '-20% 0px -60% 0px', // focused view zone
    threshold: 0
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        const index = id.replace('card-section-', '');
        
        document.querySelectorAll('.nav-item').forEach(item => {
          item.classList.remove('active');
        });
        
        const activeItem = document.querySelector(`.nav-item[data-section="${index}"]`);
        if (activeItem) {
          activeItem.classList.add('active');
        }
      }
    });
  }, observerOptions);
  
  document.querySelectorAll('.card').forEach(card => {
    observer.observe(card);
  });

  // Handle Loader on submit
  document.getElementById('docs-form').addEventListener('submit', function(e) {
    const overlay = document.getElementById('loader-overlay');
    overlay.style.display = 'flex';
    setTimeout(() => { overlay.style.opacity = '1'; }, 10);
    
    const steps = [
      "Reading MSEDCL templates...",
      "Injecting dynamic consumer data...",
      "Converting wattage & capacities...",
      "Generating output documents...",
      "Zipping package archives...",
      "Triggering ZIP download..."
    ];
    
    let stepIdx = 0;
    document.getElementById('loader-text').innerText = steps[stepIdx];
    
    const interval = setInterval(() => {
      stepIdx++;
      if (stepIdx < steps.length) {
        document.getElementById('loader-text').innerText = steps[stepIdx];
      } else {
        clearInterval(interval);
      }
    }, 600);
    
    setTimeout(() => {
      overlay.style.opacity = '0';
      setTimeout(() => {
        overlay.style.display = 'none';
      }, 300);
    }, 4200);
  });
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
            # Format and convert values based on units before rendering
            for group in GROUPS:
                for field in group["fields"]:
                    name = field["name"]
                    if field.get("unit_choices"):
                        val = data[name]
                        unit = request.form.get(f"{name}_unit", "").strip()
                        if name == "module_wattage":
                            watt_match = re.search(r"\d+", val)
                            if watt_match:
                                data[name] = f"{watt_match.group(0)} {unit}"
                        elif name in ["sanctioned_capacity_kw", "rooftop_capacity_kw", "inverter_capacity_kw"]:
                            num_match = re.search(r"[\d\.]+", val)
                            if num_match:
                                num_val = float(num_match.group(0))
                                if unit.lower() == "w":
                                    num_val = num_val / 1000.0
                                data[name] = f"{num_val:g}"

            # Auto-calculate panel capacity in Watt (count * wattage number)
            watt_match = re.search(r"\d+", str(data["module_wattage"]))
            if watt_match and count > 0:
                watt_val = int(watt_match.group(0))
                data["module_capacity_watt"] = str(count * watt_val)
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
