import zipfile
import re
from pathlib import Path

out_root = Path(__file__).parent / "output"
templates = [
    "Commissioning_Report.docx",
    "Proforma_A.docx",
    "Guarantee_Certificate.docx",
    "Annexure3.docx",
    "Annex2.docx",
]

if not out_root.exists() or not list(out_root.glob("*")):
    print("No generated outputs found in output/ directory.")
    exit(0)

all_ok = True
# Loop over each consumer output folder
for out_dir in out_root.iterdir():
    if not out_dir.is_dir():
        continue
        
    print(f"=== Verifying output for: {out_dir.name} ===")
    folder_ok = True
    for doc_name in templates:
        fpath = out_dir / doc_name
        if not fpath.exists():
            print(f"  Error: {doc_name} does not exist in output!")
            folder_ok = False
            all_ok = False
            continue
        
        with zipfile.ZipFile(fpath) as z:
            doc_xml = z.read("word/document.xml").decode("utf-8")
            
        # Look for any remaining Jinja brackets
        jinja_placeholders = re.findall(r"\{\{[^}]*\}\}", doc_xml)
        if jinja_placeholders:
            print(f"  FAIL: {doc_name} still contains Jinja placeholders:")
            for p in jinja_placeholders:
                print(f"    {p}")
            folder_ok = False
            all_ok = False
        else:
            print(f"  PASS: {doc_name} contains no unresolved Jinja placeholders.")
            
    if folder_ok:
        print(f"Result: All files for {out_dir.name} verified successfully!\n")
    else:
        print(f"Result: Verification FAILED for {out_dir.name}!\n")

if all_ok:
    print("SUCCESS: All generated documents across all folders verified successfully!")
else:
    print("FAILURE: Some documents have unresolved placeholders.")
