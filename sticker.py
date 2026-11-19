"""Prepare the project sticker values shared by the web form and the CLI."""

import re

STICKER_DEFAULTS = {
    "sticker_scheme": "PM- Surya Ghar",
    "sticker_agency_name": "S. S. PowerTech",
    "sticker_agency_contact": "9673768750",
}

PORTAL_SANCTION_REFERENCE = re.compile(
    r"(?P<office>[A-Z0-9/-]+)/Rooftop +RE/(?P<consumer>[0-9]{12})/"
    r"(?P<application>[A-Z0-9-]+)/(?P<date>[0-9]{1,2}-[A-Z]{3}-[0-9]{4})",
    re.IGNORECASE,
)


def sticker_context(data):
    reference = str(data.get("sticker_sanction_reference") or "").strip()
    if reference:
        portal = PORTAL_SANCTION_REFERENCE.fullmatch(reference)
        if portal and portal["consumer"] != str(data["consumer_number"]):
            raise ValueError("The sticker sanction reference contains a different consumer number. Correct it or leave it blank.")
    else:
        reference = str(data.get("sanction_number") or "").strip()
        date = str(data.get("sanction_date") or "").strip()
        if reference and date and not re.search(r"\bDate\s*:", reference, re.IGNORECASE):
            reference = f"{reference} Date:{date}"

    return {
        "sticker_sanction_reference": reference,
        **{name: str(data.get(name) or "").strip() or default for name, default in STICKER_DEFAULTS.items()},
    }
