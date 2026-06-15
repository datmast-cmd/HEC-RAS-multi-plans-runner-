# QCT HEC-RAS Multiplan Runner

A standalone Windows batch runner for **HEC-RAS** hydraulic models using **RAS Commander**. Run multiple plans sequentially or in parallel — no HEC-RAS GUI, no Terms & Conditions dialog, no QGIS required.

---

## Features

- **Parallel execution** — run multiple HEC-RAS plans simultaneously in isolated worker folders
- **Sequential execution** — run plans one by one with full logging
- **Auto-detect Ras.exe** — scans common HEC-RAS install paths if left blank
- **No TCU dialog** — uses `capture_output=True` internally so HEC-RAS never attaches to a console
- **Auto-install** — installs `ras-commander` automatically on first run
- **Clean logging** — timestamped results with `[OK]` / `[!!]` status per plan

---

## Files

| File | Purpose |
|------|---------|
| `run_hecras.bat` | User configuration + launcher (edit this) |
| `run_hecras.py` | Execution engine (do not edit) |

Place both files in the **same folder**. Double-click `run_hecras.bat` to run.

---

## Requirements

- Windows 10 / 11
- Python 3.9+ with `ras-commander` installed:
  ```
  pip install ras-commander
  ```
- HEC-RAS 6.x or 7.x installed

---

## Quick Start

1. Copy `run_hecras.bat` and `run_hecras.py` to a folder on your PC
2. Edit the **USER CONFIG** section at the top of `run_hecras.bat`:

```batch
set "PROJECT_FOLDER=C:\DV\HEC\Coastal Flood Model"
set "PROJECT_NAME=Coastal"
set "PLANS=ALL"
set "RUN_MODE=PAR"
set "MAX_WORKERS=3"
set "CORES_PER_PLAN=2"
set "FORCE_RERUN=YES"
set "RAS_EXE="
set "PYTHON=python"
```

3. Double-click `run_hecras.bat`

---

## Configuration

### `PROJECT_FOLDER`
Full path to the folder containing your HEC-RAS project files.
```batch
set "PROJECT_FOLDER=C:\DV\HEC\Coastal Flood Model"
```

### `PROJECT_NAME`
The project name **without** the `.prj` extension.
```batch
set "PROJECT_NAME=Coastal"
```

### `PLANS`
Plans to run. Use space-separated plan IDs or `ALL` to run every plan in the project.
```batch
set "PLANS=ALL"          :: run all plans
set "PLANS=P01 P02 P03"  :: run specific plans
set "PLANS=p01 p03"      :: case-insensitive, p prefix optional
```

### `RUN_MODE`
| Value | Description |
|-------|-------------|
| `PAR` | Parallel — all plans run simultaneously in isolated worker folders |
| `SEQ` | Sequential — plans run one by one |

### `MAX_WORKERS`
Maximum number of simultaneous HEC-RAS instances (parallel mode only).

**Recommended:** `floor(physical_cores / CORES_PER_PLAN)`

```batch
set "MAX_WORKERS=3"   :: 3 simultaneous runs
```

### `CORES_PER_PLAN`
CPU cores allocated to each HEC-RAS instance.

```batch
set "CORES_PER_PLAN=2"   :: 2 cores per plan
```

> **Rule of thumb:** `MAX_WORKERS × CORES_PER_PLAN ≤ physical CPU cores`
> Example: 12-core CPU → `MAX_WORKERS=4` + `CORES_PER_PLAN=3`

### `FORCE_RERUN`
| Value | Description |
|-------|-------------|
| `YES` | Always re-run plans, even if results already exist |
| `NO`  | Skip plans that already have results |

### `RAS_EXE`
Full path to `Ras.exe`. **Leave blank** to auto-detect from installed HEC-RAS versions (scans 7.1 → 5.0 on C: and D: drives).

```batch
set "RAS_EXE="                                                    :: auto-detect
set "RAS_EXE=C:\Program Files (x86)\HEC\HEC-RAS\7.0.1\Ras.exe"  :: explicit path
```

> ⚠️ Use the **full path with spaces** — do not use 8.3 short paths like `Program~2`.

### `PYTHON`
Python executable to use. Must have `ras-commander` installed.

```batch
set "PYTHON=python"                         :: system Python
set "PYTHON=C:\Python312\python.exe"        :: specific install
```

---

## How It Works

```
run_hecras.bat
  ├─ Validates Ras.exe, project file, Python
  ├─ Writes args to a temp file (handles paths with spaces)
  └─ Calls: python run_hecras.py --args-file <tmp>

run_hecras.py
  ├─ Reads args from temp file
  ├─ Installs ras-commander if missing
  ├─ Calls: RasCmdr.compute_plan()        (sequential)
  │         RasCmdr.compute_parallel()    (parallel)
  └─ RC internally calls:
       subprocess.run("Ras.exe -c project.prj",
                      capture_output=True)
       ↑ capture_output=True = no console = no TCU dialog
```

**Parallel mode** uses RAS Commander's native worker folder isolation:
```
Project\
Project [Worker 1]\   ← copy of project, runs plan 01
Project [Worker 2]\   ← copy of project, runs plan 02
Project [Worker 3]\   ← copy of project, runs plan 03
```
Results are consolidated back to the original project folder automatically.

---

## Example Output

```
============================================================
 QCT HEC-RAS Batch Runner
============================================================
 Project : C:\DV\HEC\Coastal Flood Model\Coastal.prj
 Plans   : P01 P02 P03
 Mode    : PAR  (workers=3, cores/plan=2)
 Force   : YES
 Ras.exe : C:\Program Files (x86)\HEC\HEC-RAS\7.0.1\Ras.exe
============================================================

==============================================================
  QCT HEC-RAS Runner  2026-06-15 15:03
==============================================================
[15:03:32]     Project  : C:\DV\HEC\Coastal Flood Model\Coastal.prj
[15:03:32]     Mode     : PARALLEL
[15:03:32]     Workers  : 3
[15:03:32]     Cores    : 2 per plan
[15:03:33] [OK] ras-commander 0.98.0 ready
[15:03:33] [>>] Initialising RAS Commander...
[15:03:33] [OK] Project loaded
[15:03:33]      Plans selected: 01, 02, 03
[15:03:33]        [01] CFHZ-3
[15:03:33]        [02] CFHZ-2
[15:03:33]        [03] MHWS-10
[15:03:33] [>>] Parallel — 3 plan(s), 3 workers × 2 cores
[15:13:21] [OK] Parallel run complete in 588.0s

==============================================================
  RESULTS SUMMARY
==============================================================
[15:13:21] [OK]   [01]  COMPLETE
[15:13:21] [OK]   [02]  COMPLETE
[15:13:21] [OK]   [03]  COMPLETE

[15:13:21]      Total time : 588.0s  (9.8 min)
[15:13:21] [OK] Succeeded  : 3 / 3
============================================================
 [OK] ALL PLANS COMPLETED SUCCESSFULLY
============================================================
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Python not found` | Set `PYTHON=` to full path, e.g. `C:\Python312\python.exe` |
| `Project not found` | Check `PROJECT_FOLDER` and `PROJECT_NAME` — no `.prj` extension |
| `ras-commander not found` | Run `pip install ras-commander` in a Command Prompt |
| Plans fail in 0.02s | Ras.exe path is wrong — check `RAS_EXE=` or leave blank for auto-detect |
| HEC-RAS TCU dialog appears | Not using RC's `compute_plan` — ensure `ras-commander` installed |
| `'AS_EXE' is not recognized` | Do not use `for...in` block in bat — use subroutine pattern (already fixed) |
| Spaces in project path | Bat uses `>>` append to temp file — paths with spaces work correctly |

---

## Compatibility

| Component | Version |
|-----------|---------|
| HEC-RAS | 6.0 – 7.1 |
| RAS Commander | 0.96+ |
| Python | 3.9 – 3.12 |
| Windows | 10, 11 |

---

## Related

- [RAS Commander](https://github.com/gpt-cmdr/ras-commander) — Python library for HEC-RAS automation

---

## License

MIT — free to use, modify and distribute.
