@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if "%PROJECT_FILE%"=="" set "PROJECT_FILE=%SCRIPT_DIR%project.prj"
if "%MAX_WORKERS%"=="" set "MAX_WORKERS=1"
if "%PLAN_NUMBERS%"=="" set "PLAN_NUMBERS=all"
if "%RUNNER_PY%"=="" set "RUNNER_PY=%SCRIPT_DIR%run_hecras.py"

if "%RAS_EXE%"=="" (
    for %%R in (
        "%ProgramFiles%\HEC\HEC-RAS\6.7\Ras.exe"
        "%ProgramFiles%\HEC\HEC-RAS\6.6\Ras.exe"
        "%ProgramFiles%\HEC\HEC-RAS\6.5\Ras.exe"
        "%ProgramFiles%\HEC\HEC-RAS\6.4\Ras.exe"
    ) do (
        if exist "%%~fR" (
            set "RAS_EXE=%%~fR"
            goto :RAS_FOUND
        )
    )
    for /f "delims=" %%R in ('where Ras.exe 2^>nul') do (
        if exist "%%~fR" (
            set "RAS_EXE=%%~fR"
            goto :RAS_FOUND
        )
    )
)

:RAS_FOUND
if not exist "%PROJECT_FILE%" (
    echo ERROR: Project file not found: "%PROJECT_FILE%"
    exit /b 2
)

if "%RAS_EXE%"=="" (
    echo ERROR: Ras.exe was not found. Set RAS_EXE explicitly.
    exit /b 2
)

if not exist "%RAS_EXE%" (
    echo ERROR: Ras.exe path does not exist: "%RAS_EXE%"
    exit /b 2
)

set "ARGS_FILE=%TEMP%\run_hecras_%RANDOM%%RANDOM%.args"
(
    echo project_file=%PROJECT_FILE%
    echo ras_exe=%RAS_EXE%
    echo max_workers=%MAX_WORKERS%
    echo plan_numbers=%PLAN_NUMBERS%
) > "%ARGS_FILE%"

set "PYTHON_CMD=python"
where python >nul 2>nul || set "PYTHON_CMD=py -3"

%PYTHON_CMD% "%RUNNER_PY%" --args-file "%ARGS_FILE%"
set "EXIT_CODE=%ERRORLEVEL%"
del /q "%ARGS_FILE%" >nul 2>nul
exit /b %EXIT_CODE%
