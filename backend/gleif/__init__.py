# SPDX-License-Identifier: EUPL-1.2
"""Local copy of the GLEIF reference data (branch feature/gleif-local).

``store``: reads the installed copy (Parquet). ``status``: state shared by the updater and the API.
``updater``: downloads the latest copy published on the repository (separate container, the only
one with internet access; the backend that analyses the registers stays offline).
"""
