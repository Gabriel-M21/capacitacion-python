import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def load_validation_script() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "run_full_validation.py"
    spec = importlib.util.spec_from_file_location("run_full_validation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_full_validation: Any = load_validation_script()


def test_pip_audit_fails_when_output_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_full_validation, "run", lambda *args, **kwargs: (0, "not json", ""))

    result = run_full_validation.step_pip_audit()

    assert result["ok"] is False
    assert "No se pudo validar" in result["summary"]


def test_pip_audit_fails_when_vulnerabilities_are_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = json.dumps(
        {
            "dependencies": [
                {
                    "name": "example-package",
                    "version": "1.0",
                    "vulns": [{"id": "CVE-0000-0000", "fix_versions": []}],
                }
            ]
        }
    )
    monkeypatch.setattr(
        run_full_validation,
        "run",
        lambda *args, **kwargs: (1, output, ""),
    )

    result = run_full_validation.step_pip_audit()

    assert result["ok"] is False
    assert result["total_deps"] == 1
    assert result["vulns"][0]["package"] == "example-package"


def test_pip_audit_passes_when_report_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    output = json.dumps(
        {
            "dependencies": [
                {"name": "order-management-system", "skip_reason": "not on PyPI"},
                {"name": "example-package", "version": "1.0", "vulns": []},
            ]
        }
    )
    monkeypatch.setattr(run_full_validation, "run", lambda *args, **kwargs: (0, output, ""))

    result = run_full_validation.step_pip_audit()

    assert result["ok"] is True
    assert result["total_deps"] == 1
    assert result["skipped_deps"] == 1
    assert result["vulns"] == []
