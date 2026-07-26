from __future__ import annotations

import argparse
import json
import os
from getpass import getpass
from pathlib import Path

from optees.interfaces.agents.ollama_harness import (
    OllamaAgentHarness,
    OllamaClient,
    OpteesToolFacade,
)
from optees.data.adapters.artifacts.configured_local_export_adapter import (
    ConfiguredLocalExportAdapter,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experimental local Ollama-to-Optees tool-calling harness."
    )
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    )
    parser.add_argument(
        "--optees-url",
        default=os.environ.get("OPTEES_BASE_URL", "http://127.0.0.1:8765"),
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Append opt-in JSONL transcripts; prompts and problem data are included.",
    )
    parser.add_argument(
        "--think",
        action="store_true",
        help="Enable model reasoning; disabled by default for bounded tool tests.",
    )
    args = parser.parse_args()

    connection_value = os.environ.get("OPTEES_AGENT_TOKEN") or getpass(
        "Paste the Optees token or copied connection JSON (input hidden): "
    )
    token = _connection_token(connection_value)
    tools = OpteesToolFacade(
        base_url=args.optees_url,
        token=token,
        export_port=ConfiguredLocalExportAdapter(),
    )
    harness = OllamaAgentHarness(
        ollama=OllamaClient(base_url=args.ollama_url, think=args.think),
        tools=tools,
        model=args.model,
        progress=lambda message: print(f"[D0] {message}", flush=True),
    )

    print("Optees Ollama D0 harness. Enter /quit to stop.")
    while True:
        try:
            prompt = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if prompt == "/quit":
            return
        if not prompt:
            continue
        try:
            run = harness.run(prompt)
        except Exception as exc:
            print(f"\nHarness error: {exc}")
            continue
        print(f"\nAssistant> {run.final_response}")
        if args.transcript is not None:
            _append_transcript(args.transcript, run.to_dict())


def _append_transcript(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


def _connection_token(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("{"):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError("The copied connection configuration is not valid JSON.") from exc
        authorization = payload.get("authorization") if isinstance(payload, dict) else None
        if not isinstance(authorization, str):
            raise ValueError("The connection configuration has no authorization field.")
        candidate = authorization.strip()
    if candidate.lower().startswith("bearer "):
        candidate = candidate[7:].strip()
    if len(candidate) < 32:
        raise ValueError("The Optees bearer token must contain at least 32 characters.")
    return candidate


if __name__ == "__main__":
    main()
