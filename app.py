#!/usr/bin/env python3
"""
Local one-time-input form for the solar project documents.

Run:
    python -m pip install -r requirements.txt
    python3 app.py
Then open http://127.0.0.1:5001 in your browser.
"""
import io
import re
import zipfile
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from flask import Flask, abort, jsonify, request, render_template_string, send_file, url_for
from docxtpl import DocxTemplate
from werkzeug.exceptions import RequestEntityTooLarge

from document_defaults import VENDOR_AND_METER_DEFAULTS
from sanction_letter import SanctionLetterError, extract_sanction_letter
from sticker import STICKER_DEFAULTS, sticker_context

# Configure logging to write to app.log in the same directory
LOG_FILE = Path(__file__).parent / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("multi_doc_writer")

app = Flask(__name__)
MAX_SANCTION_PDF_SIZE = 5 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_SANCTION_PDF_SIZE + 64 * 1024
# Pass standard Flask errors to the file logger as well
app.logger.handlers.extend(logging.getLogger().handlers)
app.logger.setLevel(logging.INFO)

TEMPLATE_DIR = Path(__file__).parent / "templates"

TEMPLATES = [
    "Commissioning_Report_TEMPLATE.docx",
    "Proforma_A_TEMPLATE.docx",
    "Guarantee_Certificate_TEMPLATE.docx",
    "Annexure3_TEMPLATE.docx",
    "Annex2_TEMPLATE.docx",
    "WorkCompletionReport_TEMPLATE.docx",
    "MeterTestingLetter_TEMPLATE.docx",
    "Sticker_TEMPLATE.docx",
]

DOCUMENT_TITLES = {
    "Commissioning_Report_TEMPLATE.docx": "Commissioning Report",
    "Proforma_A_TEMPLATE.docx": "Proforma A",
    "Guarantee_Certificate_TEMPLATE.docx": "Guarantee Certificate",
    "Annexure3_TEMPLATE.docx": "Annexure 3 Agreement",
    "Annex2_TEMPLATE.docx": "Annex 2 Vendor Agreement",
    "WorkCompletionReport_TEMPLATE.docx": "Work Completion Report",
    "MeterTestingLetter_TEMPLATE.docx": "Meter Testing Letter",
    "Sticker_TEMPLATE.docx": "Project Sticker",
}

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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


def render_document(template_name, data):
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    document = DocxTemplate(template_path)
    document.render(data, autoescape=True)
    buffer = io.BytesIO()
    document.save(buffer)
    return dedupe_docx_bytes(buffer.getvalue())


# Group fields logically for the UI
GROUPS = [
    {
        "title": "Consumer General Info",
        "icon": "user",
        "fields": [
            {"label": "Consumer Full Name", "name": "consumer_name", "ph": "SACHIN SAHDEV GAWAND", "required": True},
            {"label": "Consumer Number", "name": "consumer_number", "inputmode": "numeric", "ph": "023130009549", "required": True},
            {"label": "Mobile Number", "name": "mobile_number", "input_type": "tel", "ph": "9260557576", "required": True},
            {"label": "Email Address (optional)", "name": "email", "ph": "consumer@example.com", "inputmode": "email", "required": False},
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
            {"label": "Sanctioned Capacity", "name": "sanctioned_capacity_kw", "step": "any", "ph": "3.3", "required": True, "unit_choices": ["kW", "W"], "unit_default": "kW"},
            {"label": "Rooftop Installed Capacity", "name": "rooftop_capacity_kw", "step": "any", "ph": "3", "required": True, "unit_choices": ["kW", "W"], "unit_default": "kW"},
            {"label": "Sanction Number (optional)", "name": "sanction_number", "ph": "4138/ALIBAG-II/75755227", "required": False},
            {"label": "Sanction Date", "name": "sanction_date", "date_format": "%d-%b-%Y", "required": True},
            {"label": "PV Solar Panel Module Count", "name": "pv_module_count", "step": "1", "ph": "6", "required": True},
            {"label": "Solar Panel Module Wattage", "name": "module_wattage", "step": "any", "ph": "550", "required": True, "unit_choices": ["WP", "W", "Wp"], "unit_default": "WP"},
            {"label": "Solar Panel Module Capacity (Watt, Auto-calculated)", "name": "module_capacity_watt", "calculated": True, "ph": "3300", "required": False, "full_width": True},
            {"label": "Solar Panel Module Make / Manufacturer", "name": "module_make", "ph": "Waaree India pvt ltd", "required": True},
            {"label": "ALMM Model Number", "name": "almm_model_number", "ph": "AE14HXXXVHC10B", "required": True},
            {"label": "Inverter Capacity", "name": "inverter_capacity_kw", "step": "any", "ph": "3.3", "required": True, "unit_choices": ["kW", "W"], "unit_default": "kW"},
            {"label": "Inverter Make / Manufacturer", "name": "inverter_make", "ph": "Polycab Solar Pvt. Ltd", "required": True},
            {"label": "Inverter Model / Rating", "name": "inverter_model", "ph": "Vs-502s", "required": True},
            {"label": "MPPT / Charge Controller Count", "name": "mppt_count", "step": "1", "ph": "1", "required": True},
            {"label": "Inverter Year of Manufacturing", "name": "inverter_manufacture_year", "step": "1", "ph": "2025", "required": True},
        ]
    },
    {
        "title": "Execution & Agreement Dates",
        "icon": "calendar",
        "fields": [
            {"label": "Installation Date", "name": "installation_date", "date_format": "%d-%B-%Y", "required": True},
            {"label": "Agreement Date", "name": "agreement_date", "date_format": "%d/%m/%Y", "required": True},
            {"label": "Execution Date (Annex-2)", "name": "execution_date_text", "date_format": "%d of %B %Y", "required": True},
        ]
    },
    {
        "title": "Vendor Credentials",
        "icon": "building-2",
        "fields": [
            {"label": "Vendor Short Name", "name": "vendor_name", "ph": "S S Powertech", "required": True, "default": VENDOR_AND_METER_DEFAULTS["vendor_name"]},
            {"label": "Vendor Full Name (with M/S)", "name": "vendor_name_full", "ph": "M/S S S PowerTech", "required": True, "default": VENDOR_AND_METER_DEFAULTS["vendor_name_full"]},
            {"label": "Vendor Registered Address", "name": "vendor_address", "ph": "Ranjanpada, Post Awas, Tal. Alibag, District. Raigad 402201", "required": True, "default": VENDOR_AND_METER_DEFAULTS["vendor_address"], "full_width": True},
            {"label": "Vendor Address Suffix (Taluka/Dist/Pin)", "name": "vendor_address_suffix", "ph": "Tal: Alibag,  DIST. RAIGAD, 402201.", "required": False, "default": VENDOR_AND_METER_DEFAULTS["vendor_address_suffix"], "full_width": True},
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
        "title": "Project Sticker",
        "icon": "tag",
        "fields": [
            {"label": "Name", "name": "sticker_consumer_name", "shared_from": "consumer_name"},
            {"label": "Consumer No", "name": "sticker_consumer_number", "shared_from": "consumer_number", "inputmode": "numeric"},
            {"label": "Address", "name": "sticker_install_address", "shared_from": "install_address", "full_width": True},
            {"label": "Sticker Sanction Reference (optional)", "name": "sticker_sanction_reference",
             "hint": "Uses the sanction number and date if left blank.", "required": False, "full_width": True},
            {"label": "Scheme", "name": "sticker_scheme", "default": STICKER_DEFAULTS["sticker_scheme"], "required": False},
            {"label": "Agency Name", "name": "sticker_agency_name",
             "default": STICKER_DEFAULTS["sticker_agency_name"], "required": False},
            {"label": "Agency Contact", "name": "sticker_agency_contact", "input_type": "tel",
             "default": STICKER_DEFAULTS["sticker_agency_contact"], "required": False},
        ]
    },
    {
        "title": "Meter Testing Letter",
        "icon": "plug",
        "fields": [
            {"label": "Generation Meter Make", "name": "generation_meter_make", "ph": "Schneider electric India pvt ltd", "required": True, "default": VENDOR_AND_METER_DEFAULTS["generation_meter_make"]},
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

  .import-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  .import-controls input[type="file"] {
    flex: 1 1 230px;
    min-width: 0;
  }

  #import-status {
    margin-top: 10px;
  }

  #import-status[data-error="true"] {
    color: var(--danger);
  }

  .unit-field {
    display: flex;
    gap: 8px;
  }

  .unit-field input {
    flex: 1;
    min-width: 0;
  }

  .date-field {
    display: flex;
    gap: 8px;
  }

  .date-field input {
    flex: 1;
    min-width: 0;
  }

  .date-picker-button {
    flex-shrink: 0;
    padding: 8px 10px;
    background: var(--accent-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font: inherit;
    font-size: 0.8rem;
    cursor: pointer;
    white-space: nowrap;
  }

  .date-picker-button:hover, .date-picker-button:focus-visible {
    border-color: var(--accent);
  }

  .date-field[data-picker-ready] input::-webkit-calendar-picker-indicator {
    display: none;
  }

  .field-error, #form-errors a {
    color: var(--danger);
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

  /* Mobile Header Styles */
  .mobile-header {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 60px;
    background: var(--bg-sidebar);
    border-bottom: 1px solid var(--border-sidebar);
    color: var(--text-on-dark);
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: 1000;
  }

  .mobile-logo {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .mobile-logo .logo-text {
    font-size: 1.15rem;
    font-weight: 750;
    color: var(--text-on-dark);
  }

  .btn-menu-toggle, .btn-sidebar-close {
    background: transparent;
    border: none;
    color: var(--text-on-dark);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    border-radius: var(--radius-sm);
    transition: background 0.15s ease;
  }

  .btn-menu-toggle:hover, .btn-sidebar-close:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .btn-menu-toggle svg, .btn-sidebar-close svg {
    width: 22px;
    height: 22px;
  }

  .btn-sidebar-close {
    display: none; /* hidden on desktop */
  }

  .sidebar-logo-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    margin-bottom: 32px;
  }

  .mobile-progress-mini {
    font-size: 0.8rem;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--border-sidebar);
    border-radius: 12px;
    padding: 2px 10px;
  }

  /* Backdrop Overlay */
  .sidebar-backdrop {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(20, 22, 31, 0.5);
    z-index: 1050;
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  /* Responsive styling */
  @media (max-width: 992px) {
    .mobile-header {
      display: flex;
    }
    
    .sidebar {
      position: fixed;
      top: 0;
      left: -280px; /* Hidden offscreen */
      width: 280px;
      height: 100vh;
      z-index: 1100;
      transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 10px 0 30px rgba(0, 0, 0, 0.25);
      border-right: 1px solid var(--border-sidebar);
    }
    
    .sidebar.open {
      left: 0;
    }
    
    .btn-sidebar-close {
      display: flex;
    }

    .sidebar-logo-container {
      margin-bottom: 24px;
    }
    
    .sidebar-logo {
      margin-bottom: 0;
    }
    
    .main-content {
      margin-left: 0;
      width: 100%;
      padding: 92px 16px 32px; /* Accounts for fixed mobile header */
    }
    
    .app-header h1 {
      font-size: 1.5rem;
    }
  }
</style>
<link rel="stylesheet" href="{{ url_for('static', filename='document-preview/preview.css') }}">
<script src="{{ url_for('static', filename='document-preview/vendor/jszip.min.js') }}" defer></script>
<script src="{{ url_for('static', filename='document-preview/vendor/docx-preview.min.js') }}" defer></script>
<script src="{{ url_for('static', filename='document-preview/preview.js') }}" defer></script>
</head>
<body>

<!-- Mobile Top Header Bar -->
<div class="mobile-header">
  <button type="button" class="btn-menu-toggle" id="menu-toggle-btn" onclick="toggleSidebar()">
    <i data-lucide="menu"></i>
  </button>
  <div class="mobile-logo">
    <span class="logo-icon"><i data-lucide="sun"></i></span>
    <span class="logo-text">Solar Docs</span>
  </div>
  <div class="mobile-progress-mini">
    <span id="mobile-progress-pct">0%</span>
  </div>
</div>

<!-- Backdrop Overlay for Mobile Sidebar -->
<div class="sidebar-backdrop" id="sidebar-backdrop" onclick="toggleSidebar()"></div>

<div class="app-layout">
  <!-- Sidebar -->
  <aside class="sidebar" id="app-sidebar">
    <div class="sidebar-logo-container">
      <div class="sidebar-logo">
        <span class="logo-icon"><i data-lucide="sun"></i></span>
        <span class="logo-text">Solar Docs</span>
      </div>
      <button type="button" class="btn-sidebar-close" id="sidebar-close-btn" onclick="toggleSidebar()">
        <i data-lucide="x"></i>
      </button>
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
      <p class="subtitle">Fill the form once to generate the solar installation documents and project sticker</p>
    </header>
    
    <section class="card full-width-section" aria-labelledby="import-title">
      <h2 class="card-title" id="import-title">Import from a sanction letter</h2>
      <form id="sanction-import" method="post" enctype="multipart/form-data"
            action="{{ url_for('import_sanction_letter') }}">
        <label for="sanction-pdf">MSEDCL rooftop sanction letter (optional)</label>
        <div class="import-controls">
          <input id="sanction-pdf" type="file" name="document" accept="application/pdf,.pdf"
                 aria-describedby="import-hint" required>
          <button type="submit" class="btn-primary">Fill from PDF</button>
        </div>
        <p class="hint-text" id="import-hint">Use the original portal PDF, up to 5 MB. Review the imported values and complete the remaining fields before generating.</p>
        <p id="import-status" role="status" aria-live="polite"></p>
      </form>
    </section>

    {% if errors %}
      <section class="card full-width-section" role="alert" tabindex="-1" id="form-errors">
        <h2 class="card-title">Please check the form</h2>
        <ul>
          {% for name, message in errors.items() %}
            <li>{% if name %}<a href="#{{ name }}">{{ message }}</a>{% else %}{{ message }}{% endif %}</li>
          {% endfor %}
        </ul>
      </section>
    {% endif %}
    <form method="POST" action="{{ url_for('generate') }}" id="docs-form">
      {% for group in groups %}
        <div class="card {% if group.title in ['Solar System Specs', 'Address Information', 'MSEDCL Subdivision (Optional)'] %}full-width-section{% endif %}" id="card-section-{{ loop.index0 }}">
          <h2 class="card-title"><i data-lucide="{{ group.icon }}"></i> {{ group.title }}</h2>
          <div class="grid-fields {% if group.title in ['Consumer General Info', 'Solar System Specs', 'Execution & Agreement Dates', 'Project Sticker'] %}grid-2{% endif %}">
            {% for field in group.fields %}
              <div class="field-wrapper {% if field.full_width %}span-2{% endif %}">
                <label for="{{ field.name }}">
                  {{ field.label }}
                  {% if field.required %}<span class="required-asterisk">*</span>{% endif %}
                </label>
                {% if field.date_format %}<div class="date-field">
                {% elif field.unit_choices %}<div class="unit-field">{% endif %}
                <input
                  type="{{ 'date' if field.date_format else 'number' if field.step else field.input_type|default('text') }}"
                  id="{{ field.name }}"
                  {% if field.shared_from %}data-shared-from="{{ field.shared_from }}"
                  {% else %}name="{{ field.name }}"{% endif %}
                  value="{{ values.get(field.shared_from or field.name, field.default|default('')) }}"
                  {% if field.default %}data-default="{{ field.default }}"{% endif %}
                  aria-describedby="hint-{{ field.name }}{% if field.name in errors %} error-{{ field.name }}{% endif %}"
                  {% if field.name in errors %}aria-invalid="true"{% endif %}
                  {% if field.ph and not field.calculated %}placeholder="{{ field.ph }}"{% endif %}
                  {% if field.inputmode %}inputmode="{{ field.inputmode }}"{% endif %}
                  {% if field.step %}min="{{ 1 if field.step == '1' else 0 }}" step="{{ field.step }}"{% endif %}
                  {% if field.required %}required{% endif %}
                  {% if field.calculated or field.shared_from %}readonly{% endif %}
                >
                {% if field.date_format %}
                  <button class="date-picker-button" type="button" data-calendar-for="{{ field.name }}"
                          aria-label="Open calendar for {{ field.label }}" hidden>
                    Calendar <span aria-hidden="true">&#9662;</span>
                  </button>
                  </div>
                {% elif field.unit_choices %}
                  <select name="{{ field.name }}_unit" id="{{ field.name }}_unit" data-default="{{ field.unit_default }}" aria-label="{{ field.label }} unit">
                    {% for choice in field.unit_choices %}
                      <option value="{{ choice }}" {% if choice == values.get(field.name ~ '_unit', field.unit_default) %}selected{% endif %}>{{ choice }}</option>
                    {% endfor %}
                  </select>
                  </div>
                {% endif %}
                <span class="hint-text" id="hint-{{ field.name }}">
                  {% if field.date_format %}Select a date from the calendar.
                  {% elif field.calculated %}Panel count multiplied by wattage per panel
                  {% elif field.hint %}{{ field.hint }}
                  {% elif field.ph %}e.g. {{ field.ph }}
                  {% endif %}
                </span>
                {% if field.name in errors %}
                  <span class="field-error" id="error-{{ field.name }}">{{ errors[field.name] }}</span>
                {% endif %}
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

    <section id="document-preview" class="document-preview" aria-labelledby="document-preview-title"
             data-documents='{{ preview_documents|tojson }}' hidden></section>

    <footer>
      <p>Sanction letters are processed by the app without sending them to an external service.</p>
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
  "email": "consumer@example.com",
  "install_address": "H. NO. 1098, TAL. ALIBAG PEN CIRCLE,",
  "consumer_residential_address": "At Post Dhokawade",
  "consumer_residential_address_suffix": "TAL. ALIBAG, DIST. RAIGAD",
  "sanctioned_capacity_kw": "5.0",
  "sanctioned_capacity_kw_unit": "kW",
  "rooftop_capacity_kw": "3.3",
  "rooftop_capacity_kw_unit": "kW",
  "module_make": "Waaree India pvt ltd",
  "inverter_capacity_kw": "3.3",
  "inverter_capacity_kw_unit": "kW",
  "inverter_make": "Polycab Solar Pvt. Ltd",
  "pv_module_count": "6",
  "module_capacity_watt": "3300",
  "installation_date": "2026-07-04",
  "agreement_date": "2026-07-02",
  "execution_date_text": "2026-07-02",
  "vendor_name": "S S Powertech",
  "vendor_name_full": "M/S S S PowerTech",
  "vendor_address": "Ranjanpada, Post Awas, Tal. Alibag, District. Raigad 402201",
  "vendor_address_suffix": "Tal: Alibag,  DIST. RAIGAD, 402201.",
  "officer_designation": "Deputy Executive Engineer Alibag II",
  "subdivision_address": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201",
  "sanction_number": "4138/ALIBAG-II/82249519",
  "sanction_date": "2026-06-25",
  "capacity_kw_compact": "3.3KW",
  "almm_model_number": "AE14HXXXVHC10B",
  "module_wattage": "550",
  "module_wattage_unit": "WP",
  "total_capacity_kwp_note": "3.3KW (3300 / 1000 = 3.3)",
  "inverter_model": "Vs-502s",
  "mppt_count": "1",
  "inverter_manufacture_year": "2025",
  "generation_meter_make": "Schneider electric India pvt ltd",
  "sticker_sanction_reference": "4138/ALIBAG-II/Rooftop RE/023130009549/82249519/25-Jun-2026",
  "sticker_scheme": "PM- Surya Ghar",
  "sticker_agency_name": "S. S. PowerTech",
  "sticker_agency_contact": "9673768750",
  "meter_serial_number": "U6541057"
};

async function importSanctionLetter(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById("import-status");
  const fileInput = document.getElementById("sanction-pdf");
  const button = form.querySelector('button[type="submit"]');
  const showStatus = (message, error = false) => {
    status.textContent = message;
    status.dataset.error = String(error);
  };
  if (fileInput.files[0].size > 5 * 1024 * 1024) {
    showStatus("Choose a PDF of 5 MB or less.", true);
    return;
  }

  const formData = new FormData(form);
  button.disabled = true;
  fileInput.disabled = true;
  showStatus("Reading the sanction letter...");
  try {
    const response = await fetch(form.action, {method: "POST", body: formData});
    const result = await response.json();
    if (!response.ok) {
      showStatus(result.error || "The PDF could not be imported.", true);
      return;
    }

    const documentForm = document.getElementById("docs-form");
    const updates = Object.entries(result.fields)
      .map(([name, value]) => [documentForm.elements.namedItem(name), value])
      .filter(([field]) => field);
    const changed = updates.filter(([field, value]) => field.value !== value);
    const replacesValues = changed.some(([field]) => {
      if (field.name.endsWith("_unit")) {
        return Boolean(documentForm.elements.namedItem(field.name.slice(0, -5))?.value);
      }
      return Boolean(field.value);
    });
    if (replacesValues && !confirm("Replace the matching fields with values from the PDF? Your other entries will stay. Review them if this is a different consumer.")) {
      showStatus("Import canceled.");
      return;
    }
    for (const [field, value] of changed) {
      field.value = value;
    }
    const imported = updates.filter(([field]) => field.tagName !== "SELECT").length;
    updateProgress();
    form.reset();
    showStatus("Imported " + imported + " fields. Review the values and complete the remaining fields.");
  } catch {
    showStatus("Could not read the PDF. Try again or enter the details manually.", true);
  } finally {
    button.disabled = false;
    fileInput.disabled = false;
  }
}

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
  
  const count = countInput.valueAsNumber;
  const wattage = wattInput.valueAsNumber;
  capacityInput.value = Number.isInteger(count) && count > 0 && wattage > 0
    ? String(Number((count * wattage).toPrecision(15)))
    : "";
}

function clearData() {
  if (confirm("Clear the entries and restore the default values?")) {
    document.querySelectorAll('#docs-form input').forEach(input => {
      input.value = input.dataset.default || "";
    });
    document.querySelectorAll('#docs-form select').forEach(select => {
      select.value = select.dataset.default;
    });
    updateProgress();
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (sidebar && backdrop) {
    sidebar.classList.toggle('open');
    if (sidebar.classList.contains('open')) {
      backdrop.style.display = 'block';
      document.body.style.overflow = 'hidden';
    } else {
      backdrop.style.display = 'none';
      document.body.style.overflow = '';
    }
  }
}

// Sidebar Scroll Function
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Close sidebar on mobile after navigating
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
      toggleSidebar();
    }
  }
}

// Progress and Status calculation
function updateProgress() {
  document.querySelectorAll("[data-shared-from]").forEach(field => {
    const source = document.getElementById(field.dataset.sharedFrom);
    if (field.value !== source.value) {
      field.value = source.value;
    }
  });
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
        if (input && input.validity.valid && input.value.trim() !== "") {
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
  
  // Update mobile mini progress bar
  const mobilePct = document.getElementById('mobile-progress-pct');
  if (mobilePct) {
    mobilePct.innerText = `${pct}%`;
  }

  document.getElementById("docs-form").dispatchEvent(new Event("document-values-changed"));
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.self === window.top) {
    document.querySelectorAll("[data-calendar-for]").forEach(button => {
      const input = document.getElementById(button.dataset.calendarFor);
      if (typeof input.showPicker === "function") {
        button.addEventListener("click", () => input.showPicker());
        button.hidden = false;
        button.closest(".date-field").dataset.pickerReady = "";
      }
    });
  }

  // Initialize Lucide icons
  window.lucide?.createIcons();
  document.getElementById("form-errors")?.focus();
  document.getElementById("sanction-import").addEventListener("submit", importSanctionLetter);

  const countInput = document.getElementById("pv_module_count");
  const wattInput = document.getElementById("module_wattage");
  if (countInput) countInput.addEventListener("input", autoCalcModuleCapacity);
  if (wattInput) wattInput.addEventListener("input", autoCalcModuleCapacity);
  
  autoCalcModuleCapacity();

  document.querySelectorAll("[data-shared-from]").forEach(field => {
    const source = document.getElementById(field.dataset.sharedFrom);
    field.readOnly = false;
    const syncToSource = () => { source.value = field.value; };
    field.addEventListener("input", syncToSource);
    field.addEventListener("change", syncToSource);
  });

  // Track input to update progress
  const inputs = document.querySelectorAll('input, select');
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


def decimal_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def render_form(values=None, errors=None, status=200):
    preview_documents = [
        {"title": DOCUMENT_TITLES[template], "url": url_for("preview_document", index=index),
         "sticker": template == "Sticker_TEMPLATE.docx"}
        for index, template in enumerate(TEMPLATES)
    ]
    return render_template_string(
        FORM_HTML, groups=GROUPS, values=values or {}, errors=errors or {},
        preview_documents=preview_documents,
    ), status


def parse_document_date(value, date_format):
    try:
        return date.fromisoformat(value)
    except ValueError:
        # Accept the formats used by older versions of the web form.
        normalized = re.sub(r"^(\d{1,2})(st|nd|rd|th) ", r"\1 ", value)
        return datetime.strptime(normalized, date_format).date()


def format_document_date(value, name, date_format):
    if name == "execution_date_text":
        day = value.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix} of {value:%B %Y}"
    if name == "installation_date":
        return f"{value.day}-{value:%B-%Y}"
    return value.strftime(date_format)


@app.route("/")
def index():
    logger.info("Index page accessed (IP: %s, UA: %s)", request.remote_addr, request.headers.get("User-Agent"))
    return render_form()


@app.post("/import-sanction-letter")
def import_sanction_letter():
    size_error = "Choose a PDF of 5 MB or less."
    try:
        upload = request.files.get("document")
        if not upload or not upload.filename.lower().endswith(".pdf"):
            return jsonify(error="Choose a PDF copy of the sanction letter."), 400
        pdf_data = upload.stream.read(MAX_SANCTION_PDF_SIZE + 1)
        if len(pdf_data) > MAX_SANCTION_PDF_SIZE:
            return jsonify(error=size_error), 413
        fields = extract_sanction_letter(io.BytesIO(pdf_data))
    except RequestEntityTooLarge:
        return jsonify(error=size_error), 413
    except SanctionLetterError as error:
        return jsonify(error=str(error)), 422

    return jsonify(fields=fields)


def prepare_document_data(values):
    data = {}
    errors = {}
    numbers = {}
    units = {}

    # Older clients submitted the sanction number and date as one text value.
    sanction_number = values.get("sanction_number", "")
    if not values.get("sanction_date"):
        legacy_sanction = re.fullmatch(r"(.+?)\s+Date:\s*(.+)", sanction_number, re.IGNORECASE)
        if legacy_sanction:
            values["sanction_number"], values["sanction_date"] = legacy_sanction.groups()

    for group in GROUPS:
        for field in group["fields"]:
            if field.get("shared_from"):
                continue
            name = field["name"]
            label = field["label"]
            value = values.get(name, "") or field.get("default", "")
            data[name] = value
            if field.get("required") and not value:
                errors[name] = f"Enter {label.lower()}."
                continue

            if field.get("date_format"):
                try:
                    chosen_date = parse_document_date(value, field["date_format"])
                    values[name] = chosen_date.isoformat()
                    data[name] = format_document_date(chosen_date, name, field["date_format"])
                except ValueError:
                    errors[name] = f"Select a valid {label.lower()}."
            elif field.get("step"):
                unit = values.get(f"{name}_unit", field.get("unit_default", ""))
                allowed = field.get("unit_choices", [])
                match = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)\s*([a-zA-Z]*)", value)
                if match and match[2] and match[2].lower() in {choice.lower() for choice in allowed}:
                    if not values.get(f"{name}_unit"):
                        unit = next(choice for choice in allowed if choice.lower() == match[2].lower())
                elif match and match[2]:
                    match = None
                number = Decimal(match[1]) if match else Decimal(0)
                whole = field["step"] == "1"
                if number <= 0 or (whole and number != number.to_integral_value()):
                    kind = "whole number" if whole else "number"
                    errors[name] = f"Enter a positive {kind} for {label.lower()}."
                elif allowed and unit not in allowed:
                    errors[name] = f"Choose a unit for {label.lower()}."
                else:
                    numbers[name] = number
                    units[name] = unit
                    values[name] = match[1]
                    if allowed:
                        values[f"{name}_unit"] = unit

    for name in ("sanctioned_capacity_kw", "rooftop_capacity_kw", "inverter_capacity_kw"):
        if name in numbers:
            capacity = numbers[name] / 1000 if units[name] == "W" else numbers[name]
            data[name] = decimal_text(capacity)
    if "module_wattage" in numbers:
        data["module_wattage"] = f"{decimal_text(numbers['module_wattage'])} {units['module_wattage']}"
    if "pv_module_count" in numbers and "module_wattage" in numbers:
        data["module_capacity_watt"] = decimal_text(numbers["pv_module_count"] * numbers["module_wattage"])

    try:
        data.update(sticker_context(data))
    except ValueError as error:
        errors["sticker_sanction_reference"] = str(error)
    if data["sanction_date"]:
        data["sanction_number"] = f"{data['sanction_number'] or ' -'} Date:{data['sanction_date']}"
    return data, errors


@app.post("/document-preview/<int:index>")
def preview_document(index):
    if index >= len(TEMPLATES):
        abort(404)
    values = {name: value.strip() for name, value in request.form.items()}
    data, _ = prepare_document_data(values)
    template_name = TEMPLATES[index]
    try:
        document = render_document(template_name, data)
    except Exception:
        logger.exception("Failed to render preview for %s", template_name)
        return jsonify(error="The Word template preview could not be loaded."), 500

    response = send_file(
        io.BytesIO(document),
        mimetype=DOCX_MIME,
        download_name=template_name.replace("_TEMPLATE", ""),
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/generate", methods=["POST"])
def generate():
    values = {name: value.strip() for name, value in request.form.items()}
    consumer_name = values.get("consumer_name", "")
    data, errors = prepare_document_data(values)
    if errors:
        return render_form(values, errors, 400)

    try:
        folder = safe_folder_name(data["consumer_name"]) or "documents"
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for template_name in TEMPLATES:
                logger.info("Processing template: %s", template_name)
                out_name = template_name.replace("_TEMPLATE", "")
                zf.writestr(f"{folder}/{out_name}", render_document(template_name, data))

        logger.info("Successfully generated documents ZIP archive for '%s' (%d files)", consumer_name, len(TEMPLATES))
        mem_zip.seek(0)
        return send_file(
            mem_zip,
            as_attachment=True,
            download_name=f"{folder}_documents.zip",
            mimetype="application/zip",
        )
    except Exception as e:
        logger.exception("Failed to generate documents for '%s' due to internal error", consumer_name)
        return render_form(values, {"": "The documents could not be generated. Your entries are still here. Please try again."}, 500)


if __name__ == "__main__":
    import sys
    # Support custom port/host if user wants, e.g. for access on local network
    host = "0.0.0.0" if "--network" in sys.argv else "127.0.0.1"
    print(f"Starting server on {host} port 5001...")
    app.run(debug=True, host=host, port=5001)
