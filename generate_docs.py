#!/usr/bin/env python3
"""
generate_docs.py
-----------------
Fills all solar-project docx templates from ONE input file (JSON),
so you type each value once and get every document generated.

Usage:
    python3 generate_docs.py input.json [output_folder]

If output_folder is omitted, files go into ./output/<consumer_name>/
"""
import sys
import json
import re
from pathlib import Path
from docxtpl import DocxTemplate

TEMPLATE_DIR = Path(__file__).parent / "templates"

TEMPLATES = [
    "Commissioning_Report_TEMPLATE.docx",
    "Proforma_A_TEMPLATE.docx",
    "Guarantee_Certificate_TEMPLATE.docx",
    "Annexure3_TEMPLATE.docx",
    "Annex2_TEMPLATE.docx",
]

# Every field used by at least one template. If a field is missing from
# the input JSON, we fail LOUDLY instead of silently leaving "{{ field }}"
# in the final Word document.
REQUIRED_FIELDS = [
    "consumer_name", "consumer_number", "mobile_number", "email",
    "install_address", "consumer_residential_address",
    "sanctioned_capacity_kw", "rooftop_capacity_kw", "module_make",
    "inverter_capacity_kw", "inverter_make", "pv_module_count", "module_capacity_kw",
    "installation_date", "agreement_date", "execution_date_text",
    "vendor_name", "vendor_name_full", "vendor_address",
]

DEFAULTS = {
    "officer_designation": "Deputy Executive Engineer Alibag II",
    "subdivision_address": "CHENDHARE, TAL-ALIBAG, DIST-RAIGAD, ALIBAG II Sub-division, ALIBAG - RAIGAD, PINCODE-402201",
    "consumer_residential_address_suffix": "TAL. ALIBAG, DIST. RAIGAD",
    "vendor_address_suffix": "Tal: Alibag,  DIST. RAIGAD, 402201.",
}


def load_input(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    missing = [k for k in REQUIRED_FIELDS if k not in data or str(data[k]).strip() == ""]
    if missing:
        print("ERROR: these fields are missing/blank in your input file:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    # Fill defaults for optional fields if missing or blank
    used_defaults = []
    for k, val in DEFAULTS.items():
        if k not in data or str(data[k]).strip() == "":
            data[k] = val
            used_defaults.append(k)

    if used_defaults:
        print("\nNOTE: The following optional fields were missing and filled with defaults (Alibag subdivision):")
        for k in used_defaults:
            print(f"  - {k}: {data[k]}")
        print()

    return data


def safe_folder_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    data = load_input(input_path)

    out_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "output"
    out_dir = out_root / safe_folder_name(data["consumer_name"])
    out_dir.mkdir(parents=True, exist_ok=True)

    for template_name in TEMPLATES:
        template_path = TEMPLATE_DIR / template_name
        doc = DocxTemplate(template_path)
        doc.render(data)
        out_name = template_name.replace("_TEMPLATE", "")
        out_path = out_dir / out_name
        doc.save(out_path)
        print(f"generated: {out_path}")

    print(f"\nAll {len(TEMPLATES)} documents generated in: {out_dir}")


if __name__ == "__main__":
    main()
