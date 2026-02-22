from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_ROOT / "engine" / "ai"


def _run_cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _parse_cli_help_command_names(help_text: str) -> set[str]:
    in_commands = False
    names: set[str] = set()
    for line in help_text.splitlines():
        if line.strip() == "Commands:":
            in_commands = True
            continue
        if not in_commands:
            continue
        if line.strip() == "Options:":
            break
        match = re.match(r"^\s{2}(.+?)\s{2,}", line)
        if not match:
            continue
        spec = match.group(1).strip()
        names.add(_command_name_from_spec(spec))
    return names


def _parse_help_json() -> dict:
    return json.loads(_run_cli("help", "--json"))


def _command_name_from_spec(spec: str) -> str:
    tokens = spec.strip().split()
    name_tokens: list[str] = []
    for token in tokens:
        if token.startswith("--") or token.startswith("["):
            break
        if token.isupper():
            break
        name_tokens.append(token)
    return " ".join(name_tokens).strip()


class HelpCommandParityTests(unittest.TestCase):
    def test_help_json_matches_cli_commands(self) -> None:
        cli_help = _run_cli("--help")
        cli_commands = _parse_cli_help_command_names(cli_help)

        help_json = _parse_help_json()
        json_commands = {cmd["name"] for cmd in help_json["commands"]}

        self.assertEqual(json_commands, cli_commands)

    def test_prompt_category_commands_are_implemented(self) -> None:
        cli_help = _run_cli("--help")
        implemented = _parse_cli_help_command_names(cli_help)
        help_json = _parse_help_json()

        advertised: set[str] = set()
        for category in help_json["prompt_categories"]:
            for intent in category["intents"]:
                command = intent.get("command", "")
                if not command.startswith("ai "):
                    continue
                advertised.add(_command_name_from_spec(command[3:].strip()))

        unsupported = sorted(advertised - implemented)
        self.assertEqual(unsupported, [])


if __name__ == "__main__":
    unittest.main()
