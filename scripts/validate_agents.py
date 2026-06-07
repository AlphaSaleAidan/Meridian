#!/usr/bin/env python3
"""Agent registry validator + drift gate (masterplan Phase 4).

Run standalone (``python scripts/validate_agents.py``) or from the
``test_agent_registry`` pytest. Exits non-zero on any violation so it can gate
CI / a pre-commit hook.

Checks
------
1. Schema — each row has a unique ``name``, a known ``category``, a boolean
   ``calls_llm``, an int|null ``exec_tier``, and a ``model_tier`` that is a
   valid routing tier *iff* ``calls_llm`` is true (else null). ``class`` and
   ``module`` must be both present or both absent.
2. Resolvability — every row that declares ``class`` + ``module`` imports, and
   the attribute exists. If the class is a BaseAgent subclass, its ``.name``
   class attribute must equal the row ``name``.
3. Drift gate — every *concrete* BaseAgent subclass discovered in the code has
   a matching registry row. A new agent added without a registry entry fails.
"""
from __future__ import annotations

import importlib
import os
import pkgutil
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.ai.routing.registry_loader import parse_registry  # noqa: E402
from src.ai.routing.tiered_router import VALID_TIERS  # noqa: E402

_VALID_CATEGORIES = {
    "analytics_ml",
    "cross_reference",
    "generation",
    "orchestration",
    "voice_realtime",
    "integration",
}

# Packages that contain BaseAgent subclasses (deterministic POS + cross-ref).
_AGENT_PACKAGES = [
    "src.ai.agents",
    "src.ai.agents.cross_ref",
]


def _validate_schema(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {i}: not a mapping")
            continue
        name = row.get("name")
        loc = f"'{name}'" if name else f"row {i}"
        if not name or not isinstance(name, str):
            errors.append(f"{loc}: missing/invalid 'name'")
            continue
        if name in seen:
            errors.append(f"{loc}: duplicate name")
        seen.add(name)

        if row.get("category") not in _VALID_CATEGORIES:
            errors.append(f"{loc}: invalid category {row.get('category')!r}")

        calls_llm = row.get("calls_llm")
        if not isinstance(calls_llm, bool):
            errors.append(f"{loc}: 'calls_llm' must be a bool")
            calls_llm = bool(calls_llm)

        exec_tier = row.get("exec_tier")
        if exec_tier is not None and not isinstance(exec_tier, int):
            errors.append(f"{loc}: 'exec_tier' must be int or null")

        model_tier = row.get("model_tier")
        if calls_llm:
            if model_tier not in VALID_TIERS:
                errors.append(
                    f"{loc}: calls_llm=true requires model_tier in {sorted(VALID_TIERS)}, got {model_tier!r}"
                )
        else:
            if model_tier is not None:
                errors.append(f"{loc}: calls_llm=false requires model_tier null, got {model_tier!r}")

        has_class = bool(row.get("class"))
        has_module = bool(row.get("module"))
        if has_class != has_module:
            errors.append(f"{loc}: 'class' and 'module' must be both set or both null")
    return errors


def _validate_resolvable(rows: list[dict]) -> list[str]:
    from src.ai.agents.base import BaseAgent

    errors: list[str] = []
    for row in rows:
        cls_name, module = row.get("class"), row.get("module")
        if not cls_name or not module:
            continue
        try:
            mod = importlib.import_module(module)
        except Exception as e:
            errors.append(f"'{row['name']}': module {module} import failed: {e!r}"[:200])
            continue
        cls = getattr(mod, cls_name, None)
        if cls is None:
            errors.append(f"'{row['name']}': class {cls_name} not found in {module}")
            continue
        if isinstance(cls, type) and issubclass(cls, BaseAgent):
            declared = getattr(cls, "name", None)
            if declared != row["name"]:
                errors.append(
                    f"'{row['name']}': BaseAgent .name attribute is {declared!r}, registry says {row['name']!r}"
                )
    return errors


def _discover_base_agents() -> dict[str, str]:
    """Return ``{name: class_path}`` for every concrete BaseAgent subclass."""
    for pkgname in _AGENT_PACKAGES:
        try:
            pkg = importlib.import_module(pkgname)
        except Exception:
            continue
        for m in pkgutil.iter_modules(getattr(pkg, "__path__", [])):
            try:
                importlib.import_module(f"{pkgname}.{m.name}")
            except Exception:
                pass

    from src.ai.agents.base import BaseAgent

    def subs(cls):
        out = set(cls.__subclasses__())
        for s in list(out):
            out |= subs(s)
        return out

    found: dict[str, str] = {}
    for cls in subs(BaseAgent):
        if getattr(cls, "__abstractmethods__", None):
            continue
        name = getattr(cls, "name", None)
        if isinstance(name, str) and name and name != "base":
            found[name] = f"{cls.__module__}.{cls.__name__}"
    return found


def _validate_drift(rows: list[dict]) -> list[str]:
    registered = {r.get("name") for r in rows if isinstance(r, dict)}
    discovered = _discover_base_agents()
    return [
        f"agent '{name}' ({path}) is a BaseAgent subclass with no registry entry"
        for name, path in sorted(discovered.items())
        if name not in registered
    ]


def validate(path: str | None = None) -> list[str]:
    """Run all checks; return a flat list of error strings ([] == valid)."""
    rows = parse_registry(path)
    if not rows:
        return ["registry is empty or could not be parsed"]
    errors: list[str] = []
    errors += _validate_schema(rows)
    errors += _validate_resolvable(rows)
    errors += _validate_drift(rows)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"AGENT REGISTRY INVALID — {len(errors)} problem(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    rows = parse_registry()
    llm = sum(1 for r in rows if r.get("calls_llm"))
    print(f"agent registry OK — {len(rows)} agents ({llm} LLM-calling), no drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
