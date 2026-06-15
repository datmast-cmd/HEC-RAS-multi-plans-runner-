#!/usr/bin/env python3
"""
run_hecras.py  —  QCT HEC-RAS Batch Runner (standalone)
Runs HEC-RAS plans via RAS Commander — no QGIS or QCT plugins needed.

Key: uses subprocess.run(capture_output=True) exactly like RC does internally,
so HEC-RAS never sees a console window → no TCU dialog.

Requirements: pip install ras-commander
"""
import argparse
import inspect
import os
import subprocess
import sys
import time
from datetime import datetime


# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    icons = {"INFO": "   ", "OK": "[OK]", "FAIL": "[!!]", "STEP": "[>>]", "WARN": "[??]"}
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {icons.get(level, '   ')} {msg}", flush=True)


# ── Dependency check ──────────────────────────────────────────────────────────
def ensure_rc():
    try:
        import ras_commander
        log(f"ras-commander {ras_commander.__version__} ready", "OK")
        return True
    except ImportError:
        pass
    log("ras-commander not found — installing…", "WARN")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "ras-commander", "-q"],
        capture_output=True, text=True)
    if r.returncode == 0:
        log("ras-commander installed successfully", "OK")
        return True
    log(f"Install failed:\n{r.stderr[-300:]}", "FAIL")
    log("Run manually:  pip install ras-commander", "INFO")
    return False


# ── Args ──────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--args-file",   default="")
    p.add_argument("--project",     default="")
    p.add_argument("--plans",       default="ALL")
    p.add_argument("--mode",        default="SEQ")
    p.add_argument("--max-workers", default=2, type=int)
    p.add_argument("--cores",       default=2, type=int)
    p.add_argument("--force",       default="YES")
    p.add_argument("--ras-exe",     default="")
    args = p.parse_args()

    if args.args_file and os.path.isfile(args.args_file):
        with open(args.args_file, encoding="utf-8", errors="replace") as f:
            lines = [l.strip() for l in f.readlines()]
        # Remove blank lines
        lines = [l for l in lines if l]
        i = 0
        while i < len(lines) - 1:
            key = lines[i].lstrip("-").replace("-", "_").strip()
            # Normalise path: forward slashes → backslashes, strip quotes
            val = lines[i + 1].strip().strip('"').replace("/", os.sep)
            if   key == "project":      args.project      = normalise_path(val)
            elif key == "plans":        args.plans        = val
            elif key == "mode":         args.mode         = val
            elif key == "max_workers":
                try: args.max_workers = int(val)
                except: pass
            elif key == "cores":
                try: args.cores = int(val)
                except: pass
            elif key == "force":        args.force        = val
            elif key == "ras_exe":      args.ras_exe      = normalise_path(val)
            i += 2
    return args


# ── RC helpers ────────────────────────────────────────────────────────────────
def normalise_path(p):
    """Strip quotes, normalise slashes — bat already verified existence."""
    return p.strip().strip('"').replace("/", os.sep) if p else p



def suppress_rc_logging():
    """Suppress RC verbose INFO/WARNING logging — only show ERROR."""
    import logging
    # Suppress all ras_commander.* loggers
    root_rc = logging.getLogger("ras_commander")
    root_rc.setLevel(logging.ERROR)
    # Also suppress child loggers explicitly
    for name in logging.Logger.manager.loggerDict:
        if name.startswith("ras_commander"):
            logging.getLogger(name).setLevel(logging.ERROR)


def init_rc(prj_folder, ras_exe):
    from ras_commander import init_ras_project, RasPrj
    ras_obj = RasPrj()
    sig     = inspect.signature(init_ras_project)
    kw      = {}
    if "ras_object"    in sig.parameters: kw["ras_object"]   = ras_obj
    elif "ras_instance" in sig.parameters: kw["ras_instance"] = ras_obj
    if "suppress_logging" in sig.parameters: kw["suppress_logging"] = True
    init_ras_project(prj_folder, ras_exe, **kw)
    return ras_obj


def normalise_plan(plan_id):
    """p01 / 01 / 1  →  '01'"""
    s = str(plan_id).strip().lower().lstrip("p")
    try:    return f"{int(s):02d}"
    except: return s


def get_plan_list(ras_obj, plans_arg):
    try:
        all_ids = [normalise_plan(p) for p in
                   ras_obj.plan_df["plan_number"].tolist()]
    except Exception:
        all_ids = []

    if plans_arg.strip().upper() == "ALL":
        nums = all_ids
    else:
        nums = [normalise_plan(p) for p in plans_arg.split() if p.strip()]

    if not nums:
        log("No plans found in project", "FAIL"); sys.exit(1)

    log(f"Plans selected: {', '.join(nums)}", "INFO")
    try:
        for _, row in ras_obj.plan_df.iterrows():
            pid = normalise_plan(row.get("plan_number", ""))
            if pid in nums:
                # Try common column names for plan title
                title = (row.get("plan_title") or row.get("Title") or
                         row.get("short_id") or row.get("Short ID") or pid)
                log(f"  [{pid}] {title}", "INFO")
    except Exception:
        pass
    return nums


# ── Run engines ───────────────────────────────────────────────────────────────
def run_sequential(ras_obj, nums, ras_exe, cores, force):
    """
    Run each plan via RasCmdr.compute_plan.
    RC calls: subprocess.run(cmd, shell=True, capture_output=True)
    capture_output=True → HEC-RAS has no console → no TCU dialog.
    """
    from ras_commander import RasCmdr
    results = {}
    sig     = inspect.signature(RasCmdr.compute_plan)
    log(f"Sequential — {len(nums)} plan(s)", "STEP")

    for i, plan in enumerate(nums, 1):
        log(f"[{i}/{len(nums)}] Plan {plan}…", "STEP")
        t0 = time.time()
        try:
            kw = dict(
                ras_object      = ras_obj,
                dest_folder     = None,     # results → original project folder
                force_rerun     = force,
                num_cores       = cores,
                stream_callback = None,     # None → RC uses capture_output=True
            )
            if "dialog_watchdog" in sig.parameters:
                kw["dialog_watchdog"] = True   # RC handles OK/Yes popups
            ok = bool(RasCmdr.compute_plan(plan, **kw))
        except Exception as e:
            log(f"  Error: {e}", "FAIL")
            ok = False
        elapsed = round(time.time() - t0, 1)
        results[plan] = ok
        log(f"  Plan {plan}: {'COMPLETE' if ok else 'FAILED'} in {elapsed}s",
            "OK" if ok else "FAIL")
    return results


def run_parallel(ras_obj, nums, cores, max_workers, force):
    """
    Run all plans simultaneously via RasCmdr.compute_parallel.
    RC creates isolated worker folders, runs each Ras.exe with capture_output.
    """
    from ras_commander import RasCmdr
    log(f"Parallel — {len(nums)} plan(s), {max_workers} workers × {cores} cores", "STEP")
    t0 = time.time()
    try:
        r = RasCmdr.compute_parallel(
            plan_number = nums,
            max_workers = max_workers,
            num_cores   = cores,
            force_rerun = force,
            dest_folder = None,
            ras_object  = ras_obj,
        )
        elapsed = round(time.time() - t0, 1)
        log(f"Parallel run complete in {elapsed}s", "OK")
        return {normalise_plan(k): bool(v) for k, v in r.items()}
    except Exception as e:
        log(f"Parallel error: {e}", "FAIL")
        return {p: False for p in nums}


# ── Summary ───────────────────────────────────────────────────────────────────
def print_summary(results, elapsed):
    print()
    print("=" * 62)
    print("  RESULTS SUMMARY")
    print("=" * 62)
    failed = []
    for plan in sorted(results):
        ok = results[plan]
        log(f"  [{plan}]  {'COMPLETE' if ok else 'FAILED'}",
            "OK" if ok else "FAIL")
        if not ok:
            failed.append(plan)
    print()
    log(f"Total time : {elapsed}s  ({elapsed/60:.1f} min)", "INFO")
    log(f"Succeeded  : {len(results)-len(failed)} / {len(results)}", "OK")
    if failed:
        log(f"Failed     : {', '.join(failed)}", "FAIL")
    return 0 if not failed else 1


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    args    = parse_args()
    mode    = args.mode.strip().upper()
    force   = args.force.strip().upper() != "NO"
    ras_exe = args.ras_exe.strip()
    prj     = os.path.abspath(args.project.strip())

    print("=" * 62)
    print(f"  QCT HEC-RAS Runner  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 62)
    log(f"Project  : {prj}", "INFO")
    log(f"Mode     : {'PARALLEL' if mode=='PAR' else 'SEQUENTIAL'}", "INFO")
    log(f"Workers  : {args.max_workers}  (parallel only)", "INFO")
    log(f"Cores    : {args.cores} per plan", "INFO")
    log(f"Force    : {force}", "INFO")
    print()

    # Ensure ras-commander is installed
    if not ensure_rc():
        sys.exit(1)

    # Suppress RC verbose logging
    suppress_rc_logging()

    # Normalise path (bat already verified it exists)
    ras_exe = normalise_path(ras_exe)
    log(f"Ras.exe  : {ras_exe}", "INFO")

    # Initialise RC with project
    prj_folder = os.path.dirname(prj)
    log("Initialising RAS Commander…", "STEP")
    ras_obj = init_rc(prj_folder, ras_exe)
    log("Project loaded", "OK")
    print()

    # Get plan list
    nums = get_plan_list(ras_obj, args.plans)
    print()

    # Run
    t0 = time.time()
    if mode == "PAR":
        results = run_parallel(ras_obj, nums, args.cores, args.max_workers, force)
    else:
        results = run_sequential(ras_obj, nums, ras_exe, args.cores, force)

    sys.exit(print_summary(results, round(time.time() - t0, 1)))


if __name__ == "__main__":
    main()
