# SPDX-License-Identifier: EUPL-1.2
"""Guards the decoupling rules described in docs/architecture.md."""

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent

# For each package: the backend packages it is allowed to import.
ALLOWED_DEPENDENCIES: dict[str, set[str]] = {
    "contracts": set(),
    "dataset": {"contracts"},
    "import_engine": {"contracts"},
    "rules": {"contracts"},
    "scoring": {"contracts"},
    "reports": {"contracts"},
    "indicators": {"contracts"},
    # Local GLEIF copy (branch feature/gleif-local): store, status, updater.
    "gleif": {"contracts"},
}
# Folders of the backend that are not application modules.
NOT_MODULES = {"api", "tests", "tools", "reference", "static"}


def _imported_packages(source_file: Path) -> set[str]:
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    packages: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            packages.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            packages.add(node.module.split(".")[0])
    return packages


def _backend_packages() -> set[str]:
    return {
        path.parent.name
        for path in BACKEND_ROOT.glob("*/__init__.py")
        if not path.parent.name.startswith(".")
    }


def test_every_module_has_declared_dependencies() -> None:
    """A new module must be added to ALLOWED_DEPENDENCIES, so its imports are checked (lot 7)."""
    undeclared = _backend_packages() - set(ALLOWED_DEPENDENCIES) - NOT_MODULES
    assert not undeclared, f"Modules without declared dependencies: {sorted(undeclared)}"


def test_modules_only_depend_on_contracts() -> None:
    backend_packages = set(ALLOWED_DEPENDENCIES) | {"api"}
    violations: list[str] = []

    for package, allowed in ALLOWED_DEPENDENCIES.items():
        for source_file in (BACKEND_ROOT / package).rglob("*.py"):
            imported = _imported_packages(source_file) & backend_packages
            forbidden = imported - allowed - {package}
            if forbidden:
                relative = source_file.relative_to(BACKEND_ROOT)
                violations.append(f"{relative} imports {sorted(forbidden)}")

    assert not violations, "Forbidden dependencies between modules:\n" + "\n".join(violations)
