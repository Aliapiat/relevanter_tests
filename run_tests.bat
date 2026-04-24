@echo off
setlocal EnableExtensions

REM ============================================================
REM  Run ALL autotests in one click.
REM
REM  Usage examples:
REM    run_tests.bat                        - all tests on dev
REM    run_tests.bat --env stage            - all tests on stage (alias: staging)
REM    run_tests.bat -m smoke               - only smoke tests
REM    run_tests.bat -m "login or vacancy"  - multiple markers
REM    run_tests.bat -k test_login          - filter by name
REM    run_tests.bat -n 4                   - parallel (pytest-xdist)
REM    run_tests.bat --env dev -m smoke -n 2
REM ============================================================

cd /d "%~dp0"

REM --- Activate venv if present ---
REM Важно: НЕ пытаемся активировать `.env` — это файл с секретами
REM (ADMIN_EMAIL/ADMIN_PASSWORD), не virtualenv. Раньше здесь был
REM ложный fallback `call ".env\Scripts\activate.bat"` — убрано,
REM чтобы батник не путался и не выдавал непонятные ошибки.
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

REM --- Check pytest is available ---
where pytest >nul 2>nul
if errorlevel 1 (
    echo [ERROR] pytest not found. Install dependencies first:
    echo     pip install -r requirements.txt
    echo     playwright install chromium
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Running tests...
echo ============================================================
echo.

REM --- Run tests ---
REM No args  -> default to dev + all tests.
REM With args -> forward them to pytest as-is.
if "%~1"=="" (
    pytest --env dev
) else (
    pytest %*
)
set "EXITCODE=%ERRORLEVEL%"

REM --- Generate Allure report if CLI is installed ---
where allure >nul 2>nul
if not errorlevel 1 (
    echo.
    echo ============================================================
    echo  Generating Allure report...
    echo ============================================================
    allure generate allure-results --clean -o allure-report
    echo.
    echo Report: %CD%\allure-report\index.html
    echo Open:   allure open allure-report
)

echo.
echo ============================================================
echo  Done. pytest exit code: %EXITCODE%
echo    0  = all tests passed
echo    1  = some tests failed
echo    2+ = runner error
echo ============================================================
echo.
pause
endlocal & exit /b %EXITCODE%