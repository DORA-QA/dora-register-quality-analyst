# SPDX-License-Identifier: EUPL-1.2
"""OneGate envelope of the ACPR (Banque de France portal).

Structure, as described in the ACPR technical note on file formats::

    <XbrlDelivery>
      <XbrlDeclarationReport xmlns="http://www.onegate.eu/2010-01-01">
        <Administration>
          <From declarerType="LEI">{LEI}</From>
          <To>BDF</To>
          <Domain>DRB</Domain>
          <Response>...</Response>
        </Administration>
        <Report action="replace">
          <csv>{ZIP archive encoded in base 64}</csv>
        </Report>
      </XbrlDeclarationReport>
    </XbrlDelivery>

Element names are matched on their local name, whatever the namespace prefix.
In real deliveries the root <XbrlDelivery> has no namespace and the OneGate namespace is
declared on <XbrlDeclarationReport>. That element must be in the OneGate namespace
(ENV-011, blocking); the namespace of the root is not checked.
"""

import base64
import binascii
import re
import unicodedata
from pathlib import Path

from lxml import etree

from contracts.import_results import ExtractedZip
from contracts.messages import ValidationMessage, make_message
from import_engine.xml_validator import secure_parser_options

STRATEGY_NAME = "ACPR_ONEGATE"
ROOT_TAG = "XbrlDelivery"
NAMESPACE = "http://www.onegate.eu/2010-01-01"
EXPECTED_RECIPIENT = "BDF"
EXPECTED_DOMAINS = ("DRA", "DRB")
LEI_PATTERN = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
BASE64_CHUNK = 4 * 1024 * 1024  # multiple of 4, so chunks decode independently


class OneGateExtractionStrategy:
    """Reads a OneGate envelope: checks it and extracts the ZIP package."""

    name = STRATEGY_NAME

    def matches(self, root_tag: str) -> bool:
        return root_tag == ROOT_TAG

    def extract(self, xml_file: str, output_dir: Path) -> ExtractedZip:
        result = ExtractedZip(strategy=self.name)
        declarations = 0
        reports_with_replace = 0
        reports = 0
        payload: str | None = None
        fields: dict[str, str] = {}

        context = etree.iterparse(xml_file, events=("start", "end"), **secure_parser_options())
        for event, element in context:
            qname = etree.QName(element)
            tag = qname.localname
            is_first_declaration = (
                event == "start" and tag == "XbrlDeclarationReport" and declarations == 0
            )
            if is_first_declaration and qname.namespace != NAMESPACE:
                result.messages.append(make_message("ENV-011", value=qname.namespace or ""))
                return result
            if event == "start":
                if tag == "XbrlDeclarationReport":
                    declarations += 1
                elif tag == "Report":
                    reports += 1
                    if element.get("action") == "replace":
                        reports_with_replace += 1
                continue

            if tag in ("From", "To", "Domain") and tag not in fields:
                fields[tag] = (element.text or "").strip()
            elif tag == "csv" and payload is None:
                payload = element.text or ""
            element.clear()

        if declarations == 0:
            result.messages.append(make_message("ENV-010"))
            return result
        if declarations > 1:
            result.messages.append(make_message("ENV-002", count=declarations))
            return result

        self._check_administration(fields, result)
        if reports == 0 or reports_with_replace != reports:
            result.messages.append(make_message("ENV-007"))

        if payload is None or not payload.strip():
            result.messages.append(make_message("ENV-003"))
            return result

        zip_path = output_dir / "package.zip"
        if not _decode_base64_to_file(payload, zip_path):
            result.messages.append(make_message("ENV-004"))
            return result

        result.zip_path = str(zip_path)
        return result

    @staticmethod
    def _check_administration(fields: dict[str, str], result: ExtractedZip) -> None:
        sender = fields.get("From", "")
        if LEI_PATTERN.match(sender):
            result.sender_lei = sender
        else:
            result.messages.append(make_message("ENV-008"))

        # Recipient and domain are OneGate rules: they are checked later, once the competent
        # authority of the register is known (check_onegate_target, PO decision on #14).
        result.recipient = fields.get("To", "")
        result.domain = fields.get("Domain", "") or None


def is_acpr(authority: str | None) -> bool:
    """The competent authority declared in RT.01.01.0050 is the ACPR."""
    text = unicodedata.normalize("NFKD", authority or "").encode("ascii", "ignore").decode()
    text = " ".join(text.upper().replace("-", " ").split())
    return "ACPR" in text.split() or "AUTORITE DE CONTROLE PRUDENTIEL" in text


def check_onegate_target(
    recipient: str | None, domain: str | None, authority: str | None
) -> list[ValidationMessage]:
    """ENV-005 and ENV-006: OneGate recipient (BDF) and domain (DRB or DRA).

    These are rules of the ACPR portal: they are only applied when the register names the ACPR
    as competent authority (RT.01.01.0050), or when that authority cannot be read (decision of
    the PO, #14). ``recipient`` is None when the administration block was not read.
    """
    if recipient is None or (authority and not is_acpr(authority)):
        return []
    found = []
    if recipient != EXPECTED_RECIPIENT:
        found.append(make_message("ENV-005", value=recipient))
    if (domain or "") not in EXPECTED_DOMAINS:
        found.append(make_message("ENV-006", value=domain or ""))
    return found


def _decode_base64_to_file(payload: str, target: Path) -> bool:
    """Decode a base 64 text to a file, piece by piece. Returns False if invalid."""
    compact = "".join(payload.split())
    try:
        with target.open("wb") as handle:
            for start in range(0, len(compact), BASE64_CHUNK):
                handle.write(base64.b64decode(compact[start : start + BASE64_CHUNK], validate=True))
    except (binascii.Error, ValueError):
        target.unlink(missing_ok=True)
        return False
    return target.stat().st_size > 0
