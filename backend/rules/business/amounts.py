# SPDX-License-Identifier: EUPL-1.2
"""Consistency of the amounts between arrangements and providers (PO-35, #144; CL-44).

DQ-014   total annual expense of a provider (B_05.01.0100) lower than the sum of the annual
         expenses (B_02.01.0050) of the arrangements that reference it in B_03.02 (INFO)
DQ-015   currency of an arrangement (B_02.01.0040) different from the currency of a provider
         it references (B_05.01.0090): the amounts are not compared (INFO)

Decisions of the PO (PO-35, 03/11/2026): expert checks, severity INFO, with no effect on the
quality score (``scored: false`` in the registry). The total of a provider may exceed the sum
(services outside DORA). No conversion between currencies. Overarching arrangements and ultimate
parents at 0 are allowed: a provider whose arrangements sum to 0 is not compared. An arrangement
shared between entities appears once in B_02.01: its amount counts once.

Amounts are read as reported (a dot as decimal separator); a value that is not a number is left
to the technical checks. Nothing is corrected, nothing is logged.
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from contracts.dataset import RoIDataset
from contracts.messages import Occurrence, ValidationMessage, make_message, with_occurrences
from rules.business.common import ROW_COLUMN, by_code, rows
from rules.technical.locations import describe

# Digits an amount may have before and after the decimal point. Far beyond any real expense, they
# keep a value such as ``9E+999999`` from being written out with a million digits (red team RT-19)
# or from overflowing the sum (RT-22).
MAX_INTEGER_DIGITS = 18
MAX_DIGITS = 36


def _amount(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        amount = Decimal(value.strip())
    except InvalidOperation:
        return None
    # NaN or infinity: not an amount (left to the technical checks).
    if not amount.is_finite():
        return None
    # An absurd size is not an amount either (left to the technical checks).
    if amount and (
        amount.adjusted() >= MAX_INTEGER_DIGITS
        or amount.adjusted() < -MAX_DIGITS
        or len("".join(map(str, amount.as_tuple().digits)).rstrip("0")) > MAX_DIGITS
    ):
        return None
    return amount


def _text(amount: Decimal) -> str:
    return format(amount.normalize(), "f")


class AmountConsistencyRule:
    """DQ-014 and DQ-015: amounts of a provider against those of its arrangements."""

    id = "dq_amounts"
    codes = ("DQ-014", "DQ-015")

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        providers = by_code(dataset, "B_05.01", "c0010", "c0090", "c0100")
        arrangements = by_code(dataset, "B_02.01", "c0010", "c0040", "c0050")
        if not providers or not arrangements:
            return []
        referenced: dict[str, set[str]] = defaultdict(set)
        for link in rows(dataset, "B_03.02", "c0010", "c0020"):
            if link["c0010"] and link["c0020"]:
                referenced[link["c0020"]].add(link["c0010"])

        low_places: list[Occurrence] = []
        low_lines: list[str] = []
        currency_places: list[Occurrence] = []
        currency_lines: list[str] = []
        for code, provider in providers.items():
            refs = sorted(r for r in referenced.get(code, ()) if r in arrangements)
            if not refs:
                continue
            currency = provider["c0090"]
            other = [
                arrangements[r]
                for r in refs
                if currency and arrangements[r]["c0040"] and arrangements[r]["c0040"] != currency
            ]
            if other:
                for arrangement in other:
                    currency_places.append(
                        Occurrence(
                            table="B_02.01",
                            row=arrangement[ROW_COLUMN],
                            column="c0040",
                            value=arrangement["c0040"],
                            target_table="B_05.01",
                            target_column="c0090",
                            side="source",
                        )
                    )
                    currency_lines.append(
                        f"#{arrangement[ROW_COLUMN]} · {arrangement['c0010']!r} : "
                        f"{arrangement['c0040']} ≠ {currency} ({code!r})"
                    )
                continue
            total = _amount(provider["c0100"])
            amounts = [a for r in refs if (a := _amount(arrangements[r]["c0050"])) is not None]
            expected = sum(amounts, Decimal(0))
            if total is None or expected <= 0 or total >= expected:
                continue
            low_places.append(
                Occurrence(
                    table="B_05.01",
                    row=provider[ROW_COLUMN],
                    column="c0100",
                    value=provider["c0100"],
                    target_table="B_02.01",
                    target_column="c0050",
                    side="source",
                )
            )
            low_lines.append(
                f"#{provider[ROW_COLUMN]} · {code!r} : {_text(total)} < {_text(expected)} "
                f"({len(refs)})"
            )

        found = []
        if low_lines:
            message = make_message("DQ-014", details=describe(low_lines), count=len(low_lines))
            found.append(with_occurrences(message, low_places))
        if currency_lines:
            message = make_message(
                "DQ-015", details=describe(currency_lines), count=len(currency_lines)
            )
            found.append(with_occurrences(message, currency_places))
        return found


def amount_rules() -> list:
    return [AmountConsistencyRule()]
