# SPDX-License-Identifier: EUPL-1.2
"""EBA 724: a register must describe its reporting entity.

Applied to B_01.01 only, the table of the entity maintaining the register. The
EBA text read so far does not list the other tables, so nothing more is assumed
(see docs/sprints/sprint-1-hypotheses.md, H13).
"""

from contracts.dataset import RoIDataset
from contracts.messages import ValidationMessage, make_message

TABLES_WITH_DATA_REQUIRED = ("B_01.01",)


class ReportingEntityPresentRule:
    id = "DAT-002"

    def evaluate(self, dataset: RoIDataset) -> list[ValidationMessage]:
        return [
            make_message("DAT-002", table=table)
            for table in TABLES_WITH_DATA_REQUIRED
            if table in dataset.tables and dataset.tables[table].height == 0
        ]
