# SPDX-License-Identifier: EUPL-1.2
"""HTTP layer (FastAPI).

Exposes the engines through REST endpoints. Contains no business logic:
routes only translate HTTP requests into calls to the engines and return
models defined in ``contracts``.
"""
