# SPDX-License-Identifier: EUPL-1.2
"""Shared contracts.

Explicit models exchanged between modules (ValidationMessage, RoIDataset,
IRule, check report and scores...). Modules depend on these contracts, never on
each other. This package must not import any other backend package.
"""
