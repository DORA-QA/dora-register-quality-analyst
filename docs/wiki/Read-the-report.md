[Français](Lire-le-rapport) · **English**

# Reading the report

## 1. The verdict, at the top

| Message | Meaning |
|---|---|
| The file is valid and its tables are loaded. | No blocking finding and nothing to correct |
| The tables are loaded. Some findings should be corrected before submission. | Nothing blocking, but points to review |
| The file has blocking findings: it would be rejected as it is. | **Correct before any submission** |

## 2. "In short"

A few sentences in plain language: the general state of the register, the priorities, the most affected tables. Always start there.

## 3. The three scores

| Score | What it measures |
|---|---|
| **Regulatory score** | The official rules (EBA, ITS) and the technical checks |
| **Quality score** | All checks, expert advice included |
| **Confidence** | 100 if there is no blocking finding, 0 otherwise |

> These scores are **internal indicators**, with no regulatory value: a score of 100 does not guarantee that the authority will accept the register.

## 4. Severity of the findings

| Severity | What to do? |
|---|---|
| **BLOCKER** | The file would be rejected: you must correct it |
| **MAJOR** | Probable non-compliance: correct before submission |
| **MINOR** | Quality could be improved: correct if possible |
| **INFO** | For information, no mandatory action |

## 5. Details of a finding

Click a finding to open it:

- the plain-language **explanation** and the **reference** (EBA rule, article of the regulation, ACPR note);
- **Where**: the table, column and row concerned (row 1 = first data row);
- **Expert advice**: how to correct it, in practice.

## 6. Regulatory view and expert view

- **Regulatory view**: only what the official texts require.
- **Expert view**: in addition, the expert advice, which is more demanding. *Advice is never a regulatory non-compliance.*

## 7. Exporting

**Export the findings** produces a CSV file (for Excel) or a JSON Lines file.

- Tick **Leave out the values from the register** for an export without confidential data, which you can share more freely.
- An export **with values** contains data from your register: store it where your IT department allows it.

Every export ends with the tool's disclaimer (and, in the offline version, with a note that the GLEIF checks are absent).
