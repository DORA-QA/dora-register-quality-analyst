[Français](Installer-et-lancer) · **English**

# Installing and starting DORA QA

> ⚠️ On a **company computer**, do these steps **with the approval of your IT department** (see [Self-service and IT](Self-service-and-IT)). Your IT department can also give you a version that is already checked and signed.

DORA QA is not installed: it is a folder to unzip. No administrator rights are needed.

## 1. Download

1. Open the project's [Releases](https://github.com/DORA-QA/dora-register-quality-analyst/releases) page.
2. In the latest version, download the ZIP for your system and your version:
   - Windows: `DORA-QA-hors-ligne-…-windows-amd64.zip` (offline) or `en-ligne` (online);
   - Mac with an Apple chip (M1 and later): `DORA-QA-hors-ligne-…-macos-arm64.zip` (offline) or `en-ligne` (online);
   - Intel Mac (older models): `DORA-QA-hors-ligne-…-macos-x86_64.zip` (offline) or `en-ligne` (online);
   - Linux (x86_64, Ubuntu 22.04, Debian 12, RHEL 9 or later): `DORA-QA-hors-ligne-…-linux-x86_64.zip` (offline) or `en-ligne` (online).

   *Apple chip or Intel?* Apple menu > *About This Mac*: the "Chip" line shows Apple M…, the "Processor" line shows Intel.
3. *(Recommended, or done by the IT department)* compare the fingerprint of the file with the one in the `SHA256SUMS.txt` file of the same page.

## 2. Unzip

There is **only one ZIP** to unzip.

- **Windows**: right-click the ZIP > *Extract All…* > *Extract*. Never start the program from inside the ZIP: Windows opens it like a folder, but the program does not work there.
- **Mac**: double-click the ZIP.
- **Linux**: `unzip DORA-QA-…-linux-x86_64.zip` in a terminal (or the archive manager).

Choose a simple folder, for example `Documents`. You get a folder named after the ZIP that holds the **`DORA-QA`** folder: the program is in the latter.

```
DORA-QA-hors-ligne-1.0.0-windows-amd64\
└── DORA-QA\
    ├── DORA-QA.exe          ← start this one (Windows)
    ├── LICENSE.txt, NOTICE.txt
    └── …
```

> ℹ️ **Test builds** (acceptance, before publication): the ZIP is downloaded from the page of a run of the *Release* workflow, *Artifacts* section. It is the same ZIP, to unzip only once. Test builds produced before version 1.0.0 were wrapped in a second ZIP: they had to be unzipped twice.

## 3. Start

- **Windows**: double-click `DORA-QA.exe`.
  - If Windows displays "Windows protected your PC": this is the expected warning for an unsigned program. **On a company computer, ask your IT department.** On a personal computer: *More info* > *Run anyway*.
- **Linux**: in a terminal, from the `DORA-QA` folder, run `./Lancer-DORA-QA.sh`.
- **Mac**: double-click `Lancer-DORA-QA.command`.
  - The first time, macOS blocks it ("Apple could not verify…"): DORA QA is not notarised by Apple. **On a company Mac, ask your IT department.** On a personal Mac, see below.

### If macOS blocks DORA QA (personal Mac)

macOS marks every downloaded file as "quarantined" and blocks programs that are not notarised. The program and each of its libraries are affected: *Open Anyway* often unblocks only the first file.

**Recommended method**: remove the quarantine from the folder, in one command.

1. Open the **Terminal** application (Applications > Utilities).
2. Type `xattr -dr com.apple.quarantine ` (with the final space), then **drag the `DORA-QA` folder** into the Terminal window: its path is added.
3. Press *Return*. No password is asked.
4. Double-click `Lancer-DORA-QA.command` again.

Example: `xattr -dr com.apple.quarantine ~/Documents/DORA-QA-hors-ligne-1.0.0-macos-arm64/DORA-QA`

**Other method**: after the blocked attempt, *System Settings* > *Privacy & Security* > *Open Anyway* next to DORA QA (session password asked), then start it again; repeat if macOS blocks another file.

> Only remove the quarantine from a ZIP downloaded from the official Releases page, whose fingerprint matches `SHA256SUMS.txt`.

A black window (terminal) opens: **do not close it**, it is the engine of the tool. The browser then opens DORA QA by itself.

## 4. Accept the disclaimer

At every start, a window reminds you that the tool is provided "as is", without warranty, and that its findings are indicative. Tick the box, then click **Continue**.

## 5. Stop

Close the terminal window. The analysed register is erased and the temporary files are deleted.
