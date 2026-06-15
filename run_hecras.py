from __future__ import annotations

import argparse
import importlib
import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def parse_args_file(args_file: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path(args_file).read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#") or "=" not in item:
            continue
        key, value = item.split("=", 1)
        values[key.strip().lower()] = value.strip()
    return values


def parse_plan_numbers(raw: str) -> list[str] | None:
    value = raw.strip()
    if not value or value.lower() == "all":
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def _extract_plan_number(plan_name: str) -> str:
    match = re.search(r"(\d+)", str(plan_name))
    return match.group(1) if match else str(plan_name).strip()


def resolve_plan_numbers(project_plans: list[str], requested: list[str] | None) -> list[str]:
    available = {_extract_plan_number(plan): plan for plan in project_plans}
    if requested is None:
        return list(available.keys())
    missing = [plan for plan in requested if plan not in available]
    if missing:
        raise ValueError(f"Requested plans not found: {', '.join(missing)}")
    return requested


def ensure_ras_commander() -> Any:
    try:
        return importlib.import_module("ras_commander")
    except ImportError:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "ras-commander"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Unable to install ras-commander") from None
    return importlib.import_module("ras_commander")


def _invoke(func: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return func(*args, **kwargs)
    except TypeError:
        return func(*args)


def initialize_project(rc: Any, project_file: str, ras_exe: str | None) -> Any:
    ras_cmdr = getattr(rc, "RasCmdr", rc)
    initializers = ["initialize_project", "open_project", "load_project"]
    for method_name in initializers:
        if hasattr(ras_cmdr, method_name):
            return _invoke(getattr(ras_cmdr, method_name), project_file=project_file, ras_exe=ras_exe)
    if hasattr(ras_cmdr, "Project"):
        return _invoke(getattr(ras_cmdr, "Project"), project_file, ras_exe)
    raise RuntimeError("Unable to initialize project with ras-commander")


def get_project_plan_list(ras_obj: Any) -> list[str]:
    for name in ("get_plan_names", "get_plans", "plans"):
        if not hasattr(ras_obj, name):
            continue
        value = getattr(ras_obj, name)
        plans = value() if callable(value) else value
        if plans:
            return [str(item) for item in plans]
    raise RuntimeError("Unable to read plans from project")


def _parallel_results_to_status(plans: list[str], result: Any) -> dict[str, bool]:
    if isinstance(result, dict):
        return {str(key): bool(value) for key, value in result.items()}
    if isinstance(result, list):
        mapped: dict[str, bool] = {}
        for index, value in enumerate(result):
            mapped[plans[index]] = bool(value)
        return mapped
    if isinstance(result, bool):
        return {plan: result for plan in plans}
    return {plan: True for plan in plans}


def run_plans(rc: Any, ras_obj: Any, plans: list[str], max_workers: int) -> dict[str, bool]:
    ras_cmdr = getattr(rc, "RasCmdr", rc)
    if max_workers <= 1:
        status: dict[str, bool] = {}
        for plan in plans:
            try:
                result = _invoke(getattr(ras_cmdr, "compute_plan"), plan, ras_object=ras_obj, capture_output=True)
                status[plan] = bool(result) if result is not None else True
            except Exception:
                status[plan] = False
        return status
    result = _invoke(
        getattr(ras_cmdr, "compute_parallel"),
        plan_number=plans,
        max_workers=max_workers,
        ras_object=ras_obj,
        capture_output=True,
    )
    return _parallel_results_to_status(plans, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch execution of HEC-RAS plans via ras-commander.")
    parser.add_argument("--args-file", required=True, help="Path to key=value argument file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    cli_args = parser.parse_args(argv)
    config = parse_args_file(cli_args.args_file)

    project_file = config.get("project_file")
    if not project_file:
        print("ERROR: project_file is required.")
        return 2

    workers = int(config.get("max_workers", "1"))
    requested = parse_plan_numbers(config.get("plan_numbers", "all"))
    ras_exe = config.get("ras_exe") or None

    rc = ensure_ras_commander()
    logging.getLogger("ras_commander").setLevel(logging.WARNING)

    started = time.time()
    ras_obj = initialize_project(rc, project_file=project_file, ras_exe=ras_exe)
    project_plans = get_project_plan_list(ras_obj)
    selected_plans = resolve_plan_numbers(project_plans, requested)
    status = run_plans(rc, ras_obj, selected_plans, max_workers=workers)

    elapsed = time.time() - started
    completed = 0
    for plan in selected_plans:
        state = "COMPLETE" if status.get(plan, False) else "FAILED"
        if state == "COMPLETE":
            completed += 1
        print(f"Plan {plan}: {state}")

    total = len(selected_plans)
    success_rate = (completed / total * 100.0) if total else 0.0
    print(f"Total execution time: {elapsed:.2f}s")
    print(f"Success rate: {success_rate:.1f}% ({completed}/{total})")
    return 0 if completed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
