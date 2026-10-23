"""Answer one precise question: can scripts/check_architecture.py detect an ORM leaking
out of the adapter layer, in the situation that will actually exist once P03-01 lands?

P03-03's Business Rules require "ORM 不传出 adapter" and Architecture Constraint 4 requires
"application 不导入 adapters". The checker polices third-party imports per *member* (per
package), not per module, so this probe runs two scenarios:

  A) backend does NOT declare sqlalchemy  -> any sqlalchemy import in the backend is caught
     by the ARCH-UNDECLARED rule;
  B) backend DOES declare sqlalchemy (the state P03-01 must create, since the persistence
     adapter needs the ORM) -> the question is whether an sqlalchemy import in the backend
     API layer is still caught by anything.

Both scenarios build their layout in a throwaway temp directory, never inside the repository.
The script starts no process and only reads scripts/check_architecture.py.

Run from the repository root:  uv run python artifacts/handoffs/P03-03/zcode/probe-architecture-coverage.py
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile

root = pathlib.Path(".").resolve()
sys.path.insert(0, str(root / "scripts"))

import check_architecture as ca  # noqa: E402 - located via sys.path above

print("baseline:", len(ca.run_checks(root)["violations"]), "violations over", ca.run_checks(root).get("modules_scanned"), "modules")
print()
print("RULE TABLES (read from the checker itself):")
print("  backend layer paths    :", list(ca.LAYERS["backend"][0]))
print("  => all of apps/backend/src is ONE layer; no adapter-versus-application sub-rule exists")
for package in ("sqlalchemy", "alembic", "psycopg"):
    print(f"  {package:<10} forbidden in:", sorted(ca.THIRD_PARTY[package][1]))
print("  => ORM/driver imports are hard-forbidden only inside the domain layer")
print()


def build(declare_sqlalchemy: bool) -> pathlib.Path:
    """Lay out a minimal repo whose backend API layer imports the ORM."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="archprobe-"))
    api = tmp / "apps/backend/src/logistics_backend/api"
    api.mkdir(parents=True)
    (api / "__init__.py").write_text("", encoding="utf-8")
    (api / "leak.py").write_text(
        "from sqlalchemy.orm import Session\n"
        "def handler(session: Session) -> Session:\n"
        "    return session\n",
        encoding="utf-8",
    )
    declared = 'dependencies = ["sqlalchemy>=2.0"]\n' if declare_sqlalchemy else "dependencies = []\n"
    (tmp / "apps/backend/pyproject.toml").write_text(
        '[project]\nname = "logistics-backend"\nversion = "0.1.0"\n' + declared,
        encoding="utf-8",
    )
    return tmp


for label, declare in (("A) backend does NOT declare sqlalchemy", False), ("B) backend DOES declare sqlalchemy", True)):
    tmp = build(declare)
    try:
        report = ca.run_checks(tmp)
        found = report["violations"]
        print(f"SCENARIO {label}")
        print("  violations:", len(found))
        for violation in found:
            print(f"    {violation['code']}: {violation['detail']}")
        print(f"  ORM import in the API layer: {'DETECTED' if found else 'NOT DETECTED'}")
        print()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print("CONCLUSION")
print("  Scenario A detection comes only from ARCH-UNDECLARED, i.e. from the dependency not")
print("  being declared yet. P03-01 must add the ORM to apps/backend/pyproject.toml for the")
print("  persistence adapter to work at all, which switches the repository into scenario B.")
print("  In scenario B nothing flags an ORM import in the API or application layer, so the")
print("  obligation 'ORM must not leave the adapter' has no automated enforcement inside the")
print("  single backend layer, and acceptance criterion 3 ('dependency boundary check passes')")
print("  would be a vacuous pass for exactly that obligation.")
