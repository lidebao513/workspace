@echo off
REM Run all tests with PYTHONPATH set correctly
setlocal
set PYTHONPATH=%cd%
python -m unittest discover tests -p "test_*.py" -v
