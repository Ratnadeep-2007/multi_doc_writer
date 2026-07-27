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

FORM_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solar Docs Generator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary: #080a10;
    --bg-surface: rgba(17, 24, 43, 0.45);
    --bg-sidebar: rgba(10, 12, 22, 0.9);
    --border-color: rgba(255, 255, 255, 0.05);
    --text-primary: #f8fafc;
    --text-secondary: #64748b;
    --accent: #6366f1;
    --accent-glow: rgba(99, 102, 241, 0.15);
    --accent-hover: #818cf8;
    --accent-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
    --card-hover-border: rgba(99, 102, 241, 0.25);
    --success: #10b981;
    --success-glow: rgba(16, 185, 129, 0.15);
    --shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
    --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
  }
  
  [data-theme="cyberpunk"] {
    --bg-primary: #050508;
    --bg-surface: rgba(9, 24, 38, 0.45);
    --bg-sidebar: rgba(5, 12, 20, 0.9);
    --accent: #00f2fe;
    --accent-glow: rgba(0, 242, 254, 0.15);
    --accent-hover: #4facfe;
    --accent-gradient: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
    --card-hover-border: rgba(0, 242, 254, 0.25);
  }

  [data-theme="sunset"] {
    --bg-primary: #0d0909;
    --bg-surface: rgba(30, 16, 16, 0.45);
    --bg-sidebar: rgba(15, 8, 8, 0.9);
    --accent: #f59e0b;
    --accent-glow: rgba(245, 158, 11, 0.15);
    --accent-hover: #fbbf24;
    --accent-gradient: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
    --card-hover-border: rgba(245, 158, 11, 0.25);
  }
  
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  
  body {
    font-family: var(--font-sans);
    background: var(--bg-primary);
    background-image: 
      radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.05) 0px, transparent 50%),
      radial-gradient(at 100% 100%, rgba(168, 85, 247, 0.05) 0px, transparent 50%);
    background-attachment: fixed;
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
    width: 320px;
    background: var(--bg-sidebar);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid var(--border-color);
    padding: 40px 24px;
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
    gap: 12px;
    margin-bottom: 40px;
  }

  .logo-icon {
    font-size: 1.8rem;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 10px var(--accent-glow));
  }

  .logo-text {
    font-family: 'Outfit', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .sidebar-progress {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 32px;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 0.85rem;
  }

  .progress-label {
    color: var(--text-secondary);
    font-weight: 500;
  }

  .progress-pct {
    font-weight: 700;
    color: var(--accent-hover);
  }

  .progress-track {
    width: 100%;
    height: 6px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-bar {
    height: 100%;
    background: var(--accent-gradient);
    border-radius: 3px;
    transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 0 10px var(--accent-hover);
  }

  .sidebar-nav {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 24px;
    padding-right: 4px;
  }

  .sidebar-nav::-webkit-scrollbar {
    width: 4px;
  }

  .sidebar-nav::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
  }

  .sidebar-nav ul {
    list-style: none;
  }

  .nav-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-radius: 10px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid transparent;
    color: var(--text-secondary);
  }

  .nav-item:hover {
    background: rgba(255, 255, 255, 0.03);
    color: var(--text-primary);
  }

  .nav-item.active {
    background: var(--accent-glow);
    border-color: rgba(99, 102, 241, 0.15);
    color: var(--text-primary);
  }

  .nav-icon {
    font-size: 1.1rem;
    margin-right: 12px;
  }

  .nav-title {
    font-size: 0.9rem;
    font-weight: 500;
  }

  .nav-status-badge {
    margin-left: auto;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.1);
    transition: all 0.2s ease;
  }

  .nav-status-badge.complete {
    color: var(--success);
    font-weight: bold;
    text-shadow: 0 0 8px var(--success);
  }

  .sidebar-footer {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .btn-sample-load {
    background: var(--accent-gradient);
    border: none;
    color: white;
    padding: 12px 20px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: inherit;
    box-shadow: 0 4px 15px var(--accent-glow);
  }

  .btn-sample-load:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
  }

  .theme-picker {
    display: flex;
    justify-content: center;
    gap: 12px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 8px;
  }

  .theme-dot {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .theme-dot:hover {
    transform: scale(1.15);
  }

  .theme-dot.active {
    border-color: var(--text-primary);
  }

  .theme-indigo { background: #6366f1; }
  .theme-cyberpunk { background: #00f2fe; }
  .theme-sunset { background: #f59e0b; }

  /* Main Content Layout */
  .main-content {
    margin-left: 320px;
    flex: 1;
    padding: 60px 80px;
    max-width: 1100px;
    width: calc(100% - 320px);
  }

  .app-header {
    margin-bottom: 48px;
  }

  .app-header h1 {
    font-family: 'Outfit', sans-serif;
    font-size: 3rem;
    font-weight: 850;
    letter-spacing: -1px;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
    display: inline-block;
  }

  .app-header .subtitle {
    color: var(--text-secondary);
    font-size: 1.15rem;
    font-weight: 400;
  }

  /* Form and Cards Styles */
  form {
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  .card {
    background: var(--bg-surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 36px;
    box-shadow: var(--shadow);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    scroll-margin-top: 40px;
  }

  .card:hover {
    border-color: var(--card-hover-border);
    box-shadow: 0 20px 45px -15px var(--accent-glow);
    transform: translateY(-2px);
  }

  .card-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    margin-bottom: 28px;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 16px;
  }

  .grid-fields {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
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
    gap: 8px;
  }

  .span-2 {
    grid-column: span 2;
  }

  @media(max-width: 768px) {
    .span-2 {
      grid-column: span 1;
    }
  }

  label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
  }

  .required-asterisk {
    color: #ef4444;
    margin-left: 3px;
    font-size: 0.9rem;
  }

  /* Form Elements Control */
  input, select {
    background: rgba(10, 12, 22, 0.5);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 12px 16px;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.95rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  input {
    width: 100%;
  }

  select {
    cursor: pointer;
    min-width: 90px;
  }

  option {
    background: #0f121d;
    color: var(--text-primary);
  }

  input::placeholder {
    color: rgba(255, 255, 255, 0.2);
  }

  input:focus, select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
    background: rgba(10, 12, 22, 0.8);
  }

  .hint-text {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .submit-container {
    text-align: center;
    margin-top: 16px;
  }

  .btn-primary {
    background: var(--accent-gradient);
    border: none;
    color: white;
    padding: 18px 48px;
    font-size: 1.15rem;
    font-weight: 700;
    border-radius: 14px;
    cursor: pointer;
    box-shadow: 0 10px 25px var(--accent-glow);
    transition: all 0.2s ease;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }

  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 30px rgba(99, 102, 241, 0.45);
  }

  .btn-primary:active {
    transform: translateY(0);
  }

  footer {
    text-align: center;
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
    background: rgba(6, 8, 14, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
    transition: opacity 0.3s ease;
  }
  
  .loader-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 24px;
    padding: 48px;
    text-align: center;
    box-shadow: 0 30px 60px -10px rgba(0, 0, 0, 0.7);
    max-width: 380px;
    width: 90%;
  }
  
  .spinner {
    width: 64px;
    height: 64px;
    border: 4px solid rgba(255, 255, 255, 0.05);
    border-top: 4px solid var(--accent);
    border-radius: 50%;
    animation: spin 1s cubic-bezier(0.5, 0, 0.5, 1) infinite;
    margin: 0 auto 28px;
    box-shadow: 0 0 20px var(--accent-glow);
  }
  
  .loader-card h3 {
    font-family: 'Outfit', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .loader-card p {
    color: var(--text-secondary);
    font-size: 0.95rem;
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
      border-bottom: 1px solid var(--border-color);
      padding: 32px 24px;
    }
    
    .main-content {
      margin-left: 0;
      width: 100%;
      padding: 40px 24px;
    }
    
    .app-header h1 {
      font-size: 2.2rem;
    }
  }
</style>
</head>
<body>
<div class="app-layout">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-logo">
      <span class="logo-icon">☀️</span>
      <span class="logo-text">Solar Docs</span>
    </div>
    
    <!-- Progress Indicator -->
    <div class="sidebar-progress">
      <div class="progress-info">
        <span class="progress-label">Completion Status</span>
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
            <span class="nav-icon">{{ group.icon }}</span>
            <span class="nav-title">{{ group.title }}</span>
            <span class="nav-status-badge" id="badge-{{ loop.index0 }}">●</span>
          </li>
        {% endfor %}
      </ul>
    </nav>
    
    <!-- Theme & Quick Actions -->
    <div class="sidebar-footer">
      <button type="button" class="btn-sample-load" onclick="fillSampleData()">
        ⚡ Load Sachin Gawand Sample
      </button>
      
      <div class="theme-picker">
        <button type="button" class="theme-dot theme-indigo active" onclick="setTheme('indigo')" title="Indigo Cosmic"></button>
        <button type="button" class="theme-dot theme-cyberpunk" onclick="setTheme('cyberpunk')" title="Cyberpunk Neon"></button>
        <button type="button" class="theme-dot theme-sunset" onclick="setTheme('sunset')" title="Sunset Flame"></button>
      </div>
    </div>
  </aside>
  
  <!-- Main Contents -->
  <main class="main-content">
    <header class="app-header">
      <h1>Solar Docs Auto-Fill</h1>
      <p class="subtitle">Enter customer details once to auto-generate all 7 project installation documents</p>
    </header>
    
    <form method="POST" action="/generate" id="docs-form">
      {% for group in groups %}
        <div class="card {% if group.title in ['Solar System Specs', 'Address Information', 'MSEDCL Subdivision (Optional)'] %}full-width-section{% endif %}" id="card-section-{{ loop.index0 }}">
          <h2 class="card-title">{{ group.icon }} {{ group.title }}</h2>
          <div class="grid-fields {% if group.title in ['Consumer General Info', 'Solar System Specs', 'Execution & Agreement Dates'] %}grid-2{% endif %}">
            {% for field in group.fields %}
              <div class="field-wrapper {% if field.full_width %}span-2{% endif %}">
                <label for="{{ field.name }}">
                  {{ field.label }}
                  {% if field.required %}<span class="required-asterisk">*</span>{% endif %}
                </label>
                {% if field.unit_choices %}
                  <div style="display: flex; gap: 8px; width: 100%;">
                    <input 
                      type="text" 
                      id="{{ field.name }}" 
                      name="{{ field.name }}" 
                      placeholder="{{ field.ph }}" 
                      {% if field.default %}value="{{ field.default }}"{% endif %}
                      {% if field.required %}required{% endif %}
                      style="flex: 1;"
                    >
                    <select 
                      name="{{ field.name }}_unit" 
                      id="{{ field.name }}_unit"
                    >
                      {% for choice in field.unit_choices %}
                        <option value="{{ choice }}" {% if choice == field.unit_default %}selected{% endif %}>{{ choice }}</option>
                      {% endfor %}
                    </select>
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
          📥 Generate & Download ZIP Package
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

// Sidebar Scroll Function
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// Theme Setting Function
function setTheme(themeName) {
  document.documentElement.setAttribute('data-theme', themeName);
  document.querySelectorAll('.theme-dot').forEach(dot => {
    dot.classList.remove('active');
  });
  const activeDot = document.querySelector(`.theme-${themeName}`);
  if (activeDot) {
    activeDot.classList.add('active');
  }
  localStorage.setItem('solar-docs-theme', themeName);
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
        badge.innerHTML = "✓";
        badge.className = "nav-status-badge complete";
      } else {
        badge.innerHTML = "●";
        badge.className = "nav-status-badge";
      }
    }
  });
  
  const pct = totalRequired > 0 ? Math.round((filledRequired / totalRequired) * 100) : 0;
  document.getElementById('progress-pct').innerText = `${pct}%`;
  document.getElementById('progress-bar').style.width = `${pct}%`;
}

document.addEventListener("DOMContentLoaded", () => {
  // Restore theme
  const savedTheme = localStorage.getItem('solar-docs-theme') || 'indigo';
  setTheme(savedTheme);

  const countInput = document.getElementById("pv_module_count");
  const wattInput = document.getElementById("module_wattage");
  if (countInput) countInput.addEventListener("input", autoCalcModuleCapacity);
  if (wattInput) wattInput.addEventListener("input", autoCalcModuleCapacity);
  
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
