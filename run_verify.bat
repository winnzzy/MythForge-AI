@echo off
cd /d c:\Users\HP\MythForge-Ai\MythForge-AI
python -m pytest tests/test_workflow/test_workflow_engine.py -q --tb=short --no-header > verify_output.txt 2>&1
echo EXIT_CODE=%ERRORLEVEL% >> verify_output.txt