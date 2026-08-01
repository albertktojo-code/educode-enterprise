from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.services.release import scan_migration_sql, validate_revision_id


def revision_metadata(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                values[node.target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return {"file": path.name, "revision": values.get("revision", ""), "down_revision": values.get("down_revision")}


def analyze_revisions(directory: Path) -> dict[str, Any]:
    revisions = [revision_metadata(path) for path in sorted(directory.glob("*.py")) if path.name != "__init__.py"]
    ids = [item["revision"] for item in revisions if item["revision"]]
    parents = {item["down_revision"] for item in revisions if item["down_revision"]}
    heads = sorted(set(ids) - parents)
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    invalid_ids = {item: validate_revision_id(item) for item in ids if validate_revision_id(item)}
    return {"revision_count": len(revisions), "heads": heads, "duplicate_ids": duplicate_ids, "invalid_ids": invalid_ids, "revisions": revisions}


def generate_offline_sql(backend_dir: Path) -> tuple[str, str]:
    process = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        return "", process.stderr.strip()
    return process.stdout, ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Validação não destrutiva das migrations do EduCode")
    parser.add_argument("--backend-dir", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    backend_dir = Path(args.backend_dir).resolve()
    analysis = analyze_revisions(backend_dir / "alembic" / "versions")
    sql, error = generate_offline_sql(backend_dir)
    sql_scan = scan_migration_sql(sql) if sql else {"safe": False, "destructive_operations": [], "error": error}
    blockers: list[str] = []
    if len(analysis["heads"]) != 1:
        blockers.append("A cadeia Alembic deve possuir exatamente um head")
    if analysis["duplicate_ids"]:
        blockers.append("Há IDs de migration duplicados")
    if analysis["invalid_ids"]:
        blockers.append("Há IDs incompatíveis com alembic_version VARCHAR(32)")
    if error:
        blockers.append("Não foi possível gerar o SQL offline")
    if sql_scan.get("destructive_operations"):
        blockers.append("O SQL contém operações destrutivas e exige aprovação manual")
    report = {"ready": not blockers, "blockers": blockers, "chain": analysis, "sql": sql_scan}
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report)
    raise SystemExit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
