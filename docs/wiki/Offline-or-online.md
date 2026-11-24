[Français](Hors-ligne-ou-en-ligne) · **English**

# Choosing your version: offline or online

| | **Offline** | **Online** |
|---|---|---|
| File to download | `DORA-QA-hors-ligne-…zip` | `DORA-QA-en-ligne-…zip` |
| Internet connection | **Never** | **At start-up only**, a few seconds to a few minutes |
| LEI checks against the GLEIF (existence, status, country, ultimate parent) | Not available (the screen says so) | Yes, on a public copy of the GLEIF data updated every night |
| All other checks | Yes | Yes |
| IT department approval | To use the tool | To use the tool **and** for the outgoing Internet connection |

## How to choose

- **By default, take the offline version.** It is the easiest to get approved: no network traffic.
- **Take the online version** if you also want to check your LEI against the GLEIF and your IT department allows the connection to GitHub.

## What happens when the online version starts

1. The tool shows a waiting screen: **no register is accepted** meanwhile.
2. It downloads the latest public copy of the GLEIF data (about 90 MB), only if it has changed.
3. It disconnects, then the import screen opens. **Your register is never sent over the Internet.**

If the download fails (no network, firewall), the tool still starts: it uses the previous copy, or states that the GLEIF checks are not evaluated.
