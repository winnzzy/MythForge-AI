import subprocess, sys
r = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/test_workflow/test_workflow_engine.py', '-q', '--tb=line', '--no-header'],
    capture_output=True, text=True, timeout=300
)
with open('test_final_result.txt', 'w') as f:
    f.write(r.stdout + '\n' + r.stderr)
print(f'EXIT_CODE: {r.returncode}')
print(f'TESTS: {r.stdout.strip().split(chr(10))[-1] if r.stdout.strip() else "no output"}')