[Français](Questions-frequentes) · **English**

# Frequently asked questions

**Does my register go on the Internet?**
No. The analysis runs entirely on your computer. Only the online version connects, at start-up, to download public GLEIF data, and never during an analysis.

**Will a register without findings necessarily be accepted by the authority?**
No. DORA QA gives indications; the authority remains the sole judge. The reporting entity remains responsible for its register.

**The browser does not open.**
Look at the terminal window: it shows the address to open (for example `http://127.0.0.1:8765`). Copy it into your browser.

**Windows or macOS refuses to start the program.**
This is normal for an unsigned program. On a company computer, **check with your IT department**; do not bypass the warning yourself. See [Install and start](Install-and-start).

**My antivirus blocks or deletes DORA QA.**
Contact your IT department. Never disable the antivirus.

**The firewall asks for network access.**
Offline version: click "Cancel", the tool does not need it. Online version: check with your IT department.

**The screen says "checks not available in this offline version".**
You are using the offline version: this is normal. For these checks, you need the [online version](Offline-or-online), with the approval of your IT department.

**The "Online update in progress" screen stays on (online version).**
The tool is downloading the GLEIF copy; please wait. After 15 minutes, it gives up and starts without a new copy. If this happens again, the network connection is probably blocked: check with your IT department.

**The row number of a finding does not match my file.**
Row 1 is the first **data** row: the header is not counted.

**I think a finding is wrong.**
Open a ["Wrong finding" issue](https://github.com/DORA-QA/dora-register-quality-analyst/issues/new/choose) with the code of the finding and the regulatory source, **without attaching a real register**. For a confidential request: [dora-qa@proton.me](mailto:dora-qa@proton.me).

**How do I get a new version?**
New versions are published in the [Releases](https://github.com/DORA-QA/dora-register-quality-analyst/releases). On a company computer, the update goes through your IT department.
