@echo off
REM ---------------------------------------------------------------------------
REM  WolfeyBot test runner.  Uses the project virtualenv; works from any folder
REM  (paths are resolved relative to this file, so cwd does not matter).
REM
REM    run_tests.bat                         run the whole suite (concise)
REM    run_tests.bat -k switch               pass any extra args to pytest
REM    run_tests.bat tests/test_turn1_decisions.py
REM
REM  -o addopts=-q overrides pytest.ini's default -v so the full-suite run stays
REM  short; extra args (%*) are appended and win for anything you pass.
REM ---------------------------------------------------------------------------
"%~dp0.venv\Scripts\python.exe" -m pytest -o addopts=-q %*
