[Français](Installer-et-lancer) · **English**

# Installing and starting DORA QA

> ⚠️ On a **company computer**, do these steps **with the approval of your IT department** (see [Self-service and IT](Self-service-and-IT)). Your IT department can also give you a version that is already checked and signed.

DORA QA is not installed: it is a folder to unzip. No administrator rights are needed.

## 1. Download

1. Open the project's [Releases](https://github.com/DORA-QA/dora-register-quality-analyst/releases) page.
2. In the latest version, download the ZIP for your system and your version:
   - Windows: `DORA-QA-hors-ligne-…-windows-amd64.zip` (offline) or `en-ligne` (online);
   - Mac (Apple chip): `DORA-QA-hors-ligne-…-macos-arm64.zip` (offline) or `en-ligne` (online).
3. *(Recommended, or done by the IT department)* compare the fingerprint of the file with the one in the `SHA256SUMS.txt` file of the same page.

## 2. Unzip

- **Windows**: right-click the ZIP > *Extract All…* Never start the program from inside the ZIP.
- **Mac**: double-click the ZIP.

Choose a simple folder, for example `Documents\DORA-QA`.

## 3. Start

- **Windows**: double-click `DORA-QA.exe`.
  - If Windows displays "Windows protected your PC": this is the expected warning for an unsigned program. **On a company computer, ask your IT department.** On a personal computer: *More info* > *Run anyway*.
- **Mac**: double-click `Lancer-DORA-QA.command`.
  - The first time, macOS blocks it. **On a company Mac, ask your IT department.** On a personal Mac: *System Settings* > *Privacy & Security* > *Open Anyway* next to DORA QA, then start it again.

A black window (terminal) opens: **do not close it**, it is the engine of the tool. The browser then opens DORA QA by itself.

## 4. Accept the disclaimer

At every start, a window reminds you that the tool is provided "as is", without warranty, and that its findings are indicative. Tick the box, then click **Continue**.

## 5. Stop

Close the terminal window. The analysed register is erased and the temporary files are deleted.
