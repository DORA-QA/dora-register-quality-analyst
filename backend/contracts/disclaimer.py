# SPDX-License-Identifier: EUPL-1.2
"""Disclaimer of DORA QA (decision of 23/11/2026, texts A8).

Shown in a blocking window at every launch of the interface, at the end of every export and in
``GET /about``. The interface keeps its own copy of the same texts (``frontend/src/i18n``); a test
checks that both stay identical.
"""

DISCLAIMER = {
    "fr": (
        "DORA QA est un outil gratuit fourni « en l'état », sans garantie. Ses constats et "
        "conseils sont indicatifs : ils reposent sur la lecture des textes réglementaires et sur "
        "l'expérience des experts du projet, mais ne remplacent pas un avis juridique ou "
        "réglementaire et ne constituent pas une attestation de conformité opposable. Un "
        "registre sans constat peut encore être rejeté par l'autorité compétente. L'entité "
        "déclarante reste seule responsable du contenu et de la remise de son registre "
        "d'information. Le développeur décline toute responsabilité quant à l'usage des "
        "résultats."
    ),
    "en": (
        'DORA QA is free software provided "as is", without warranty. Its findings and advice '
        "are indicative: they are based on the reading of the regulatory texts and on the "
        "experience of the project's experts, but they do not replace legal or regulatory advice "
        "and do not constitute an enforceable certificate of compliance. A register without "
        "findings may still be rejected by the competent authority. The reporting entity remains "
        "solely responsible for the content and submission of its register of information. The "
        "developer accepts no liability for the use of the results."
    ),
}

LICENCE = "EUPL-1.2 (European Union Public Licence v. 1.2)"


def disclaimer(language: str) -> str:
    return DISCLAIMER.get(language, DISCLAIMER["en"])
