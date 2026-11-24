[Français](Fiche-pour-la-DSI) · **English**

# Sheet to send to your IT department

*Page to send as is to your IT department or CISO to ask for permission to use DORA QA.*

## The tool in brief

DORA QA (DORA Register Quality Analyst) checks the quality of a DORA register of information (Implementing Regulation (EU) 2024/2956, EBA taxonomy 4.0) **before it is submitted** to the authority. Free software under the **EUPL 1.2** licence, public source code: https://github.com/DORA-QA/dora-register-quality-analyst

## Technical characteristics

| Point | Detail |
|---|---|
| Installation | None: portable folder to unzip, **no administrator rights** |
| Content | PyInstaller executable (Python 3.13) bundling the engine (FastAPI) and the web interface (React) |
| Network listening | `127.0.0.1` only, port 8765 (or a free port): **not reachable from the network** |
| Register data | Read in the system temporary folder, **purged** at the end of the analysis and at shutdown; nothing is sent outside; no telemetry |
| **Offline** version | **No outgoing traffic**; the download module is not included in the executable |
| **Online** version | At start-up only, outgoing HTTPS to `api.github.com`, `github.com` and GitHub download domains (`*.githubusercontent.com`) for a public copy of the GLEIF data (about 90 MB, CC0 licence); no register accepted during this download; 20 s network timeout, 15 min maximum duration |
| Cache (online version) | Public GLEIF copy in `%LOCALAPPDATA%\DORA-QA\gleif` (Windows) or `~/Library/Caches/DORA-QA/gleif` (macOS); never any register data |
| Exports | Created by the user, on request; an export "with values" contains register data |
| Signature | **Unsigned** executables (no Authenticode, no Apple notarisation) |
| Integrity | `SHA256SUMS.txt` fingerprints and SBOM (SPDX) published with each release |
| Updates | Manual: no automatic update of the program |

## Options for the IT department

- **Check** the SHA-256 fingerprint and, if desired, audit the source code and the SBOM.
- **Rebuild and sign** the tool with the company certificate: [signing guide](https://github.com/DORA-QA/dora-register-quality-analyst/blob/main/docs/signature-entreprise.md) (in French; `signtool`, `codesign`, MSI package for Intune or SCCM).
- **Choose the version**: offline (no traffic) or online (GitHub traffic at start-up).
- **"Sources" variant** for computers that block unsigned executables: runs from VS Code with the official (signed) Python, libraries provided, offline installation.
- **Docker stack** for an isolated server deployment.

## Contact

Security: private report through the repository's [Security](https://github.com/DORA-QA/dora-register-quality-analyst/security) tab, or [dora-qa@proton.me](mailto:dora-qa@proton.me) (subject "SECURITY"). Confidential requests: [dora-qa@proton.me](mailto:dora-qa@proton.me).

> DORA QA is provided "as is", without warranty; its findings are indicative and do not constitute a certificate of compliance.
