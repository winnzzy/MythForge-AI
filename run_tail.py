import subprocess, sys
# Run only tests from TestCheckpointManager onwards (where previous output stopped)
r = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/test_workflow/test_workflow_engine.py', 
     '-q', '--tb=short', '--no-header',
     '-k', 'checkpoint or manifest or integration or dag_helpers or workflow_result or executor'],
    capture_output=True, text=True, timeout=300
)
with open('tail_result.txt', 'w') as f:
    f.write(r.stdout + '\n' + r.stderr)
print(f'EXIT_CODE: {r.returncode}')
lines = r.stdout.strip().split('\n')
print(f'LAST_LINE: {lines[-1] if lines else "no output"}')