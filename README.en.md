# DORA Register Quality Analyst (DORA QA)

**Local quality analysis of a DORA register of information, before it is submitted to the competent authority.**
[Français](README.md) · **English**

DORA QA reads a register of information (Implementing Regulation (EU) 2024/2956, EBA taxonomy 4.0) as an **xBRL-CSV ZIP** package or in its **OneGate XML envelope** (ACPR), then produces a report of findings ranked by severity. Each finding comes with a plain-language explanation, its reference (EBA rule, article of the ITS, ACPR note) and advice on how to fix it.

> ⚠️ **Disclaimer.** DORA QA is free software provided "as is", without warranty. Its findings and advice are indicative: they are based on the reading of the regulatory texts and on the experience of the project's experts, but they do not replace legal or regulatory advice and do not constitute an enforceable certificate of compliance. A register without findings may still be rejected by the competent authority. The reporting entity remains solely responsible for the content and submission of its register of information. The developer accepts no liability for the use of the results.

## Privacy

- **Everything happens on your computer.** The register is never sent over the Internet; the interface and the engine only answer on `127.0.0.1`.
- **Nothing is kept.** The file is read in a temporary folder, purged at the end of the analysis and when the application stops.
- **Open, auditable code** for your security teams, under the EUPL 1.2 licence.

## Two versions

| Version | Checks | Connection |
|---|---|---|
| **DORA QA offline** | All checks, **except** those that query the GLEIF (the screen says so) | None, ever |
| **DORA QA online** | All checks, **including** the verification of the LEI against a local copy of the GLEIF data | At start-up only, to update the public copy of the GLEIF data; no register is accepted during this download, and no connection takes place afterwards |

Choose the offline version if your IT department forbids any outgoing connection.

## Installation

Download from the [Releases](../../releases) the ZIP for your system and the chosen version (`DORA-QA-hors-ligne-…` for offline or `DORA-QA-en-ligne-…` for online), check its SHA-256 fingerprint (file `SHA256SUMS.txt` of the release), unzip it, then run:

- **Windows**: `DORA-QA.exe`. The program is not signed: SmartScreen may display "Windows protected your PC"; click *More info*, then *Run anyway*.
- **macOS**: `Lancer-DORA-QA.command` (ZIP `macos-arm64` for Macs with an Apple chip, `macos-x86_64` for Intel Macs). The application is not notarised: on first launch, macOS blocks it. Open *System Settings > Privacy & Security*, then click *Open Anyway* next to DORA QA.
- **Linux** (x86_64, glibc 2.35 or later: Ubuntu 22.04, Debian 12, RHEL 9 and later): `./Lancer-DORA-QA.sh` in a terminal.

The browser opens on the interface. Close the terminal window to stop the application.

Does your company want an executable signed in its own name? See [Signing DORA QA with your own certificate](docs/signature-entreprise.md) (in French) or open a [signing request](../../issues/new/choose). For a confidential request: [dora-qa@proton.me](mailto:dora-qa@proton.me).

## What is checked

- **Shape of the submission**: OneGate XML envelope, structure of the xBRL-CSV ZIP package, naming, encoding, expected or extra files.
- **Data format**: headers, types, dates, closed lists of the EBA taxonomy, lengths, identifiers (LEI, EUID, national codes).
- **EBA validation rules** active for taxonomy 4.0, and integrity rules between tables.
- **Expert checks**: consistency between tables, subcontracting chain, amounts, ultimate parent, concentration.
- **GLEIF** (online version): existence, status, country and ultimate parent of the LEI.

The report gives three scores (regulatory, quality, confidence) and an "In short" summary, and can be exported as CSV and JSON Lines.

## From the sources

Prerequisites: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 22.

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && uv sync --frozen
uv run python ../portable/launcher.py
```

Building the ZIPs: `uv run --project backend --with pyinstaller python portable/build.py` (offline version) or `… build.py --online` (online version). Without a ZIP, choose the version with `DORA_QA_EDITION=online`. A Docker stack (`docker compose up --build`) remains available for an isolated server deployment.

User guide for business teams: [wiki](../../wiki). Technical documentation (in French): [architecture](docs/architecture.md), [scores](docs/scores.md), [GLEIF](docs/gleif.md), [closed lists](docs/listes-fermees.md), [national identifiers](docs/referentiel-identifiants-nationaux.md).

## Contributing

Bug reports and proposals are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md#english). **Never send a real register**, even partially: use the fictitious data sets of `sample-data/`. Security vulnerabilities: see [SECURITY.md](SECURITY.md#english). Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md#english).

## Contact

[dora-qa@proton.me](mailto:dora-qa@proton.me) for confidential requests (enterprise signing, deployment). Public questions and reports: [issues](../../issues/new/choose). Never send a real register, through any channel.

## Licence

Code published under the **[EUPL 1.2](LICENSE)** (European Union Public Licence). All official language versions of the licence have the same value: the English version is in [LICENSE](LICENSE), the French version in [LICENCE.fr.txt](LICENCE.fr.txt). Third-party data and texts: see [NOTICE](NOTICE).
