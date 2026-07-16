from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from enum import IntEnum
from pathlib import Path
from typing import Sequence

from optees.application.contracts.capability import ProblemValidation
from optees.application.contracts.errors import ErrorCode, ErrorDetail, StructuredError
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    JobStatus,
    MathematicalStatus,
)
from optees.application.contracts.json_value import dumps_json


class ExitCode(IntEnum):
    SUCCESS = 0
    INVALID_INPUT = 2
    CAPABILITY_UNAVAILABLE = 3
    INFEASIBLE = 4
    CANCELLED = 5
    TECHNICAL_FAILURE = 6
    UNBOUNDED = 7
    NOT_SOLVED = 8


class _UsageError(ValueError):
    pass


class _ContractArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError(message)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except _UsageError as exc:
        error = StructuredError(
            code=ErrorCode.INVALID_REQUEST,
            message="Invalid command-line arguments.",
            details=(ErrorDetail(path="$.arguments", message=str(exc)),),
        )
        return _emit_error(error, ExitCode.INVALID_INPUT)

    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    try:
        with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
            from optees.composition.local_agent import (
                create_local_optimization_service,
            )

            service = create_local_optimization_service()
            outcome = _execute(args, service)
    except Exception:
        error = StructuredError(
            code=ErrorCode.INTERNAL_ERROR,
            message="The headless command failed before producing a result.",
        )
        return _emit_error(error, ExitCode.TECHNICAL_FAILURE)

    if captured_stdout.getvalue() or captured_stderr.getvalue():
        print(
            "optees-cli: backend diagnostics were suppressed; inspect the JSON result.",
            file=sys.stderr,
        )

    if isinstance(outcome, StructuredError):
        return _emit_error(outcome, _error_exit_code(outcome.code))

    _write_json(outcome)
    if isinstance(outcome, ExecutionEnvelope):
        return int(_execution_exit_code(outcome))
    return int(ExitCode.SUCCESS)


def _build_parser() -> argparse.ArgumentParser:
    parser = _ContractArgumentParser(
        prog="optees-cli",
        description="Headless access to versioned Optees solver contracts.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-capabilities", help="List registered capabilities.")

    for command in ("validate", "solve"):
        command_parser = commands.add_parser(command)
        command_parser.add_argument("capability_id")
        command_parser.add_argument(
            "input",
            nargs="?",
            default="-",
            help="JSON file path, or '-' for stdin (default).",
        )
    return parser


def _execute(args, service):
    if args.command == "list-capabilities":
        return {
            "contract_version": "1",
            "capabilities": list(service.list_capabilities()),
        }

    payload = _read_payload(args.input)
    if isinstance(payload, StructuredError):
        return payload
    if args.command == "validate":
        return service.validate(args.capability_id, payload)
    return service.solve(args.capability_id, payload)


def _read_payload(source: str) -> dict[str, object] | StructuredError:
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text("utf-8")
    except OSError:
        return StructuredError(
            code=ErrorCode.INVALID_REQUEST,
            message="The input file could not be read.",
            details=(
                ErrorDetail(
                    path="$.input",
                    message="Verify that the path exists and is readable.",
                    code="unreadable_input",
                ),
            ),
        )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return StructuredError(
            code=ErrorCode.INVALID_REQUEST,
            message="The input is not valid JSON.",
            details=(
                ErrorDetail(
                    path="$",
                    message=f"JSON syntax error at line {exc.lineno}, column {exc.colno}.",
                    code="invalid_json",
                ),
            ),
        )
    if not isinstance(payload, dict):
        return StructuredError(
            code=ErrorCode.INVALID_REQUEST,
            message="The problem payload must be a JSON object.",
            details=(ErrorDetail(path="$", message="Expected a JSON object."),),
        )
    return payload


def _write_json(outcome: object) -> None:
    if isinstance(outcome, (ExecutionEnvelope, ProblemValidation, StructuredError)):
        payload = outcome.to_dict()
    else:
        payload = outcome
    assert isinstance(payload, dict)
    print(dumps_json(payload))


def _emit_error(error: StructuredError, exit_code: ExitCode) -> int:
    _write_json(error)
    print(f"optees-cli: {error.message}", file=sys.stderr)
    return int(exit_code)


def _error_exit_code(code: ErrorCode) -> ExitCode:
    if code in {ErrorCode.INVALID_REQUEST, ErrorCode.VALIDATION_FAILED}:
        return ExitCode.INVALID_INPUT
    if code in {ErrorCode.CAPABILITY_NOT_FOUND, ErrorCode.DEPENDENCY_UNAVAILABLE}:
        return ExitCode.CAPABILITY_UNAVAILABLE
    if code is ErrorCode.CANCELLATION_NOT_SUPPORTED:
        return ExitCode.CANCELLED
    return ExitCode.TECHNICAL_FAILURE


def _execution_exit_code(envelope: ExecutionEnvelope) -> ExitCode:
    if envelope.job_status is JobStatus.CANCELLED:
        return ExitCode.CANCELLED
    if envelope.job_status is JobStatus.FAILED:
        return ExitCode.TECHNICAL_FAILURE
    if envelope.mathematical_status in {
        MathematicalStatus.OPTIMAL,
        MathematicalStatus.FEASIBLE,
    }:
        return ExitCode.SUCCESS
    if envelope.mathematical_status is MathematicalStatus.INFEASIBLE:
        return ExitCode.INFEASIBLE
    if envelope.mathematical_status is MathematicalStatus.UNBOUNDED:
        return ExitCode.UNBOUNDED
    return ExitCode.NOT_SOLVED


if __name__ == "__main__":
    raise SystemExit(main())
