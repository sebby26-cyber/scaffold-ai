"""
ai_validate.py — Schema validation for canonical YAML files.

Validates .ai/state/*.yaml against JSON schemas under schemas/.
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _load_yaml(path: Path) -> dict:
    """Load a YAML file. Tries PyYAML first, falls back to basic parsing."""
    text = path.read_text()
    if yaml:
        return yaml.safe_load(text) or {}
    # Minimal fallback: use json if the YAML happens to be JSON-compatible
    # For real use, install PyYAML
    raise ImportError(
        "PyYAML is required for YAML parsing. Install it: pip install pyyaml"
    )


def _load_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text())


def _validate_type(value, expected_type: str) -> bool:
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    return isinstance(value, expected)


def _validate_value(value, schema: dict, path: str = "") -> list[str]:
    """Simple recursive JSON Schema validator (subset of draft-07)."""
    errors = []
    if value is None:
        return errors

    expected_type = schema.get("type")
    if expected_type and not _validate_type(value, expected_type):
        errors.append(f"{path}: expected type '{expected_type}', got '{type(value).__name__}'")
        return errors

    if expected_type == "object" and isinstance(value, dict):
        required = schema.get("required", [])
        for req in required:
            if req not in value:
                errors.append(f"{path}: missing required field '{req}'")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errors.extend(_validate_value(v, props[k], f"{path}.{k}"))

    if expected_type == "array" and isinstance(value, list):
        items_schema = schema.get("items", {})
        for i, item in enumerate(value):
            errors.extend(_validate_value(item, items_schema, f"{path}[{i}]"))

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value '{value}' not in enum {schema['enum']}")

    return errors


def validate_file(yaml_path: Path, schema_path: Path) -> list[str]:
    """Validate a YAML file against a JSON schema.

    Returns list of error messages (empty = valid).
    """
    try:
        data = _load_yaml(yaml_path)
    except Exception as e:
        return [f"Failed to load {yaml_path}: {e}"]

    try:
        schema = _load_schema(schema_path)
    except Exception as e:
        return [f"Failed to load schema {schema_path}: {e}"]

    return _validate_value(data, schema, yaml_path.name)


def validate_submodule_integrity(project_root: Path) -> list[str]:
    """Check that no files inside submodules have been modified.

    Returns list of error messages (empty = clean).
    """
    from .guard import detect_submodule_paths

    errors: list[str] = []
    for sub_path in detect_submodule_paths(project_root):
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(sub_path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    errors.append(
                        f"Submodule modified: {sub_path.name}/{line.strip()}"
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return errors


def validate_all(
    ai_dir: Path,
    schemas_dir: Path,
    project_root: Path | None = None,
) -> dict[str, list[str]]:
    """Validate all canonical YAML files against their schemas.

    Also checks submodule integrity if project_root is provided.

    Returns {filename: [errors]} dict.
    """
    mapping = {
        "team.yaml": "team.schema.json",
        "board.yaml": "board.schema.json",
        "approvals.yaml": "approvals.schema.json",
        "commands.yaml": "commands.schema.json",
    }

    results = {}
    for yaml_name, schema_name in mapping.items():
        yaml_path = ai_dir / "state" / yaml_name
        schema_path = schemas_dir / schema_name
        if not yaml_path.exists():
            results[yaml_name] = [f"File not found: {yaml_path}"]
            continue
        if not schema_path.exists():
            results[yaml_name] = [f"Schema not found: {schema_path}"]
            continue
        results[yaml_name] = validate_file(yaml_path, schema_path)

    # Submodule integrity check
    if project_root is not None:
        sub_errors = validate_submodule_integrity(project_root)
        if sub_errors:
            results["submodule_integrity"] = sub_errors
        else:
            results["submodule_integrity"] = []

    # Capabilities consistency check
    caps_errors = validate_capabilities_consistency(ai_dir)
    if caps_errors:
        results["capabilities_consistency"] = caps_errors
    else:
        results["capabilities_consistency"] = []

    return results


def validate_capabilities_consistency(ai_dir: Path) -> list[str]:
    """Check that capabilities.yaml is consistent with help/guide output.

    If worker_bees.supported is true, the help builder must include the
    worker bees category. This prevents capability regression.
    """
    errors: list[str] = []
    caps_path = ai_dir / "state" / "capabilities.yaml"

    if not caps_path.exists():
        return []  # No capabilities file is fine — help shows unconfigured state

    if yaml is None:
        return ["PyYAML required for capabilities validation"]

    try:
        caps = yaml.safe_load(caps_path.read_text()) or {}
    except Exception as e:
        return [f"Failed to parse capabilities.yaml: {e}"]

    worker_cfg = caps.get("worker_bees", {})
    if worker_cfg.get("supported"):
        # Verify the help builder would include worker bees
        from .help.builder import _load_capabilities, _build_prompt_categories
        loaded = _load_capabilities(ai_dir)
        categories = _build_prompt_categories(loaded)
        bee_cats = [c for c in categories if "Worker" in c.name or "Bee" in c.name]
        if not bee_cats:
            errors.append(
                "capabilities.yaml has worker_bees.supported=true but "
                "help/guide does not include a Worker Bees category"
            )

    return errors
