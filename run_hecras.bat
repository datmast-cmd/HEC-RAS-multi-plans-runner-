@echo off
setlocal EnableDelayedExpansion
:: ============================================================
::  QCT HEC-RAS Batch Runner V1.0
::  Edit USER CONFIG then double-click to run.
::  Place this .bat in the same folder as run_hecras.py
:: ============================================================

:: ── USER CONFIG ─────────────────────────────────────────────

set "PROJECT_FOLDER=C:\DV\HEC\Coastal Flood Model"
set "PROJECT_NAME=Coastal"

:: List of plans: P01 P02 P03 .. or ALL
set "PLANS=P01 P02"

:: Run mode SEQ or PAR
set "RUN_MODE=PAR"
set "MAX_WORKERS=3"
set "CORES_PER_PLAN=2"
set "FORCE_RERUN=YES"

:: Ras.exe — leave blank to auto-detect from installed HEC-RAS versions
set "RAS_EXE=C:\Program Files (x86)\HEC\HEC-RAS\7.0.1\Ras.exe"

:: Python with ras-commander: pip install --upgrade ras-commander
set "PYTHON=python"

:: ── END USER CONFIG ─────────────────────────────────────────

:: ── AUTO-DETECT Ras.exe ──────────────────────────────────────
:: If RAS_EXE is blank, search common install locations newest-first
if "%RAS_EXE%"=="" (
    echo  [>>] Auto-detecting Ras.exe...
    for %%V in (7.1 7.0.1 7.0 6.6 6.5 6.4 6.3 6.2 6.1 6.0 5.0.7 5.0.3 5.0) do (
        if "%RAS_EXE%"=="" (
            for %%D in (
                "C:\Program Files (x86)\HEC\HEC-RAS\%%V\Ras.exe"
                "C:\Program Files\HEC\HEC-RAS\%%V\Ras.exe"
                "D:\Program Files (x86)\HEC\HEC-RAS\%%V\Ras.exe"
                "D:\Program Files\HEC\HEC-RAS\%%V\Ras.exe"
            ) do (
                if "%RAS_EXE%"=="" if exist %%D set "RAS_EXE=%%~D"
            )
        )
    )
)

if "%RAS_EXE%"=="" (
    echo  [!!] ERROR: Could not find Ras.exe
    echo       Set RAS_EXE= in this bat file
    pause & exit /b 1
)
echo  [OK] Ras.exe : %RAS_EXE%

:: ── VERIFY PROJECT FILE ───────────────────────────────────────
set "PRJ_FILE=%PROJECT_FOLDER%\%PROJECT_NAME%.prj"
if not exist "%PRJ_FILE%" (
    echo  [!!] ERROR: Project not found:
    echo       %PRJ_FILE%
    pause & exit /b 1
)
echo  [OK] Project : %PRJ_FILE%

:: ── VERIFY PYTHON ─────────────────────────────────────────────
"%PYTHON%" --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [!!] ERROR: Python not found: %PYTHON%
    echo       Set PYTHON= to a valid Python executable
    pause & exit /b 1
)

echo.
echo ============================================================
echo  QCT HEC-RAS Batch Runner
echo ============================================================
echo  Project : %PRJ_FILE%
echo  Plans   : %PLANS%
echo  Mode    : %RUN_MODE%  (workers=%MAX_WORKERS%, cores/plan=%CORES_PER_PLAN%)
echo  Force   : %FORCE_RERUN%
echo  Ras.exe : %RAS_EXE%
echo ============================================================
echo.

:: Write args to temp file — >> avoids CMD space-in-path issues
set "ARGS=%TEMP%\qct_hecras_%RANDOM%.txt"
if exist "%ARGS%" del "%ARGS%"
>>"%ARGS%" echo --project
>>"%ARGS%" echo %PRJ_FILE%
>>"%ARGS%" echo --plans
>>"%ARGS%" echo %PLANS%
>>"%ARGS%" echo --mode
>>"%ARGS%" echo %RUN_MODE%
>>"%ARGS%" echo --max-workers
>>"%ARGS%" echo %MAX_WORKERS%
>>"%ARGS%" echo --cores
>>"%ARGS%" echo %CORES_PER_PLAN%
>>"%ARGS%" echo --force
>>"%ARGS%" echo %FORCE_RERUN%
>>"%ARGS%" echo --ras-exe
>>"%ARGS%" echo %RAS_EXE%

"%PYTHON%" -u "%~dp0run_hecras.py" --args-file "%ARGS%"
set "EC=%ERRORLEVEL%"
del "%ARGS%" 2>nul

echo.
if %EC% EQU 0 (
    echo  [OK] ALL PLANS COMPLETED SUCCESSFULLY
) else (
    echo  [!!] ONE OR MORE PLANS FAILED
)
echo ============================================================
pause
endlocal
