# HEC-RAS-multi-plans-runner-
HEC-RAS Multi-Plans Runner is a lightweight, standalone Python tool for batch execution of multiple HEC-RAS plans in parallel or sequential mode. 

## Quick start

1. Set environment variables (optional):
   - `PROJECT_FILE` (default: `project.prj` beside `run_hecras.bat`)
   - `RAS_EXE` (auto-detected when omitted)
   - `MAX_WORKERS` (default: `1`)
   - `PLAN_NUMBERS` (default: `all`, or comma list like `01,02`)
2. Run:
   - `run_hecras.bat`

The batch script validates paths, writes arguments to a temp file, and launches `run_hecras.py`.
The Python runner ensures `ras-commander` is installed, initializes the project, computes selected plans
sequentially or in parallel, and prints a result summary.
