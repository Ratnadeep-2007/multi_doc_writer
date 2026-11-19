"""Extract reviewable form values from MSEDCL rooftop sanction letters."""

import re
from datetime import datetime

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from sticker import PORTAL_SANCTION_REFERENCE, STICKER_DEFAULTS


class SanctionLetterError(ValueError):
    """The upload could not be imported as a sanction letter."""


def extract_sanction_letter(stream):
    if stream.read(5) != b"%PDF-":
        raise SanctionLetterError("Choose a PDF copy of the sanction letter.")
    stream.seek(0)

    try:
        reader = PdfReader(stream)
        if reader.is_encrypted:
            raise SanctionLetterError("Choose an unlocked copy of the sanction letter.")
        if len(reader.pages) > 10:
            raise SanctionLetterError("Upload the sanction letter on its own (up to 10 pages).")
        text = "\f".join(page.extract_text() or "" for page in reader.pages)
    except SanctionLetterError:
        raise
    except (PyPdfError, OSError, ValueError, RecursionError) as error:
        raise SanctionLetterError("This PDF could not be read. Download a fresh copy and try again.") from error

    if not text.strip():
        raise SanctionLetterError("This PDF has no selectable text. Use the original portal PDF or enter the details manually.")

    return extract_sanction_fields(text)


def extract_sanction_fields(text):
    # Keep page and line boundaries so one letter cannot supply another letter's fields.
    raw_pages = [page.splitlines() for page in text.split("\f")]
    pages = [("\n".join(" ".join(line.split()) for line in lines), lines) for lines in raw_pages]
    flags = re.IGNORECASE | re.MULTILINE
    sanction_header = re.compile(
        r"^Sanction No *: *([A-Z0-9/-]+) +Date *: *(\d{1,2}-[A-Za-z]+-\d{4}) *$",
        flags,
    )
    matches = [(page, lines, match) for page, lines in pages for match in sanction_header.finditer(page)]
    if len(matches) > 1:
        raise SanctionLetterError("This PDF contains multiple sanction headers. Upload one sanction letter at a time.")
    unsupported = "This PDF does not match the MSEDCL rooftop sanction letter format."
    if not matches:
        raise SanctionLetterError(unsupported)

    text, lines, sanction = matches[0]
    title = re.search(r"^Maharashtra State Electricity Distribution Co\. Ltd\.?$", text, flags)
    subject = re.search(
        r"^Subject:\s*Sanction Letter for\s+[\d.]+\s*KW\s+Rooftop\s+Renewable Energy Generating System\s+"
        r"for Consumer Number\s+([0-9]{12})\b",
        text,
        flags,
    )
    if not (title and subject and title.start() < sanction.start() < subject.start()):
        raise SanctionLetterError(unsupported)

    fields = {"consumer_number": subject[1]}
    try:
        fields["sanction_date"] = datetime.strptime(sanction[2], "%d-%b-%Y").date().isoformat()
    except ValueError:
        pass
    else:
        fields["sanction_number"] = sanction[1]

    # Map the normalized header positions back to the unmodified recipient lines.
    recipient_start = text.count("\n", 0, sanction.end()) + 1
    recipient_end = text.count("\n", 0, subject.start())
    recipient_block = "\n".join(lines[recipient_start:recipient_end])
    recipient = re.search(r"^[ \t]*To,[ \t]*\n(?:[ \t]*\n)*([^\n]+)\n([\s\S]+)", recipient_block, flags)
    if recipient:
        fields["consumer_name"] = recipient[1].strip()
        details = recipient[2]
        address = details.split("\n", 1)[0].strip()
        if address and not re.match(r"(?:Pin[ \t]*code|Mobile|E-?mail(?:[ \t]+ID)?)[ \t]*:", address, flags):
            fields["install_address"] = address
        mobile = re.search(
            r"^[ \t]*Mobile[ \t]*:[ \t]*([0-9]{10})(?=[ \t]*(?:[,;]|E-?mail\b|$))",
            details,
            flags,
        )
        if mobile:
            fields["mobile_number"] = mobile[1]
        # Accept inline and standalone email labels while leaving an empty label blank.
        email = re.search(
            r"(?<![\w-])E-?mail(?:[ \t]+ID)?[ \t]*:\s*"
            r"([A-Z0-9.!_%+'~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+)\b",
            details,
            flags,
        )
        if email:
            fields["email"] = email[1]

    load = re.search(r"^Sanctioned Load\s+([0-9]+(?:\.[0-9]+)?)\s*KW\b", text[subject.end():], flags)
    if load and float(load[1]) > 0:
        fields["sanctioned_capacity_kw"] = load[1]
        fields["sanctioned_capacity_kw_unit"] = "kW"

    if "sanction_number" in fields:
        for line in text[subject.end():].splitlines():
            label = re.match(r"Sanction No *: *(.*)$", line, flags)
            if not label:
                continue
            reference = PORTAL_SANCTION_REFERENCE.fullmatch(label[1])
            if (reference and reference["consumer"] == fields["consumer_number"]
                    and f"{reference['office']}/{reference['application']}".casefold() == sanction[1].casefold()
                    and reference["date"].casefold() == sanction[2].casefold()):
                fields["sticker_sanction_reference"] = label[1]
                break

    scheme = re.search(r"^Scheme Name *: *(.*?)(?: +Agency Name *:|$)", text[subject.end():], flags)
    if scheme:
        name = re.sub(r"^Applied At +", "", scheme[1], flags=re.IGNORECASE).strip()
        if name:
            if re.sub(r"[^a-z]", "", name.lower()).startswith("pmsuryaghar"):
                name = STICKER_DEFAULTS["sticker_scheme"]
            fields["sticker_scheme"] = name

    return fields
