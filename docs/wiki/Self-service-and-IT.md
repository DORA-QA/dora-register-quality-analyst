[Français](Autonomie-et-DSI) · **English**

# What you can do on your own, what you must check with your IT department

DORA QA is designed to be used by business teams, without installation or administrator rights. But it handles your **register of information**, which is sensitive data, and it runs on a **company computer**: some steps belong to your IT department and to your CISO (security).

> **Simple rule**: anything that touches the **workstation**, the **network** or the **processing of real data** is decided with the IT department **before** you start. Once the tool is authorised, the analysis and the reading of the results are entirely in your hands.

## ✅ What you can do on your own

| Action | Why it is risk-free |
|---|---|
| Read the documentation and this wiki | No action on the computer |
| Discover the tool **on a personal computer**, with the **fictitious examples** provided (`exemples` folder) | No company data, no company computer |
| Once DORA QA is **authorised by the IT department** on your computer: start the tool, analyse your registers, change the language | Everything stays on your computer; nothing is sent or kept |
| Read the report, filter the findings, switch between the regulatory view and the expert view | Simple consultation |
| Correct your register in your usual tool, then analyse it again | You work on your own files |
| Export the findings **without the register values** ("Leave out the values from the register" box) | The export only contains codes, explanations and locations |
| Answer "Cancel" if the firewall asks for network access (offline version) | The analysis does not need the network |
| Report a finding that seems wrong to you, **without attaching a real register** | See the [FAQ](FAQ) |

## ⚠️ What you must check with your IT department

| Topic | Why | What to ask for |
|---|---|---|
| **Running DORA QA on a company computer** | The program is not signed: Windows (SmartScreen) and macOS prevent it from starting. **Do not bypass these warnings yourself** on a company computer. | Permission to use the tool, or a version signed by the company (see the [IT sheet](IT-department-sheet)) |
| **Analysing a real register** | The register contains confidential data (contracts, providers, amounts) | Confirmation that the tool is approved for data of this confidentiality level |
| **Choosing the online version** | It connects to the Internet at start-up (GitHub) to download the public copy of the GLEIF data | Opening of the outgoing connection, or use of the **offline** version |
| **Where to store the exports** | An export **with values** contains register data | The authorised location (shared folder, document management tool) and the retention period |
| **Antivirus alert, program blocked or deleted** | The computer is protected by rules you must not change | Handling of the alert by the IT department: never disable the antivirus |
| **Installing new versions** | A new version is a new program | The update process (who downloads, who checks, who deploys) |
| **Deployment to several people** | Several computers, possibly an installation package | A centralised deployment (Intune, SCCM…) with a signed version |

## Recommended process

1. **You**: discover the tool on a personal computer with the fictitious examples.
2. **You → IT**: send the [IT sheet](IT-department-sheet) with your need (offline or online version, number of users).
3. **IT**: checks, authorises, possibly signs and deploys the tool.
4. **You**: analyse your registers on your own before each submission.

> **Never, through any channel**: do not send a real register to the authors of the project, neither in a GitHub issue nor by e-mail.
