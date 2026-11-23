# SPDX-License-Identifier: EUPL-1.2
"""Import engine.

Turns a deposited file (XML envelope or ZIP package) into validated tables:
file type detection, XML validation, ZIP extraction, ZIP validation, package
validation and CSV import. Depends only on ``contracts``.
"""
