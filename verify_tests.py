"""Direct test verification without pytest subprocess."""
import sys, os
sys.path.insert(0, '.')

# Import all test classes
from tests.test_workflow.test_workflow_engine import *

def run_test(cls, method_name):
    """Run a single test method."""
    try:
        instance = cls()
        getattr(instance, method_name)()
        return True, None
    except Exception as e:
        return False, str(e)

# Collect all test classes and methods
test_classes = [
    TestStageDefinition, TestRetryPolicy, TestStageState, TestWorkflowResult,
    TestStageRegistry, TestDependencyGraph, TestExecutionPlanner, TestResumePlanner,
    TestRetryPlanner, TestEventDispatcher, TestWorkflowEvents, TestCheckpointManager,
    TestManifestHooks, TestIntegrationScenarios, TestDAGHelpers, TestWorkflowResultExtended,
    TestWorkflowExecutor
]

total = 0
passed = 0
failed = 0
errors = []

for cls in test_classes:
    instance = cls()
    if hasattr(instance, 'setup_method'):
        instance.setup_method()
    methods = [m for m in dir(instance) if m.startswith('test_')]
    for method in methods:
        if hasattr(instance, 'setup_method'):
            instance.setup_method()
        total += 1
        ok, err = run_test(cls, method)
        if ok:
            passed += 1
        else:
            failed += 1
            errors.append(f"{cls.__name__}.{method}: {err}")

with open('verify_result.txt', 'w') as f:
    f.write(f"TOTAL: {total}\n")
    f.write(f"PASSED: {passed}\n")
    f.write(f"FAILED: {failed}\n")
    if errors:
        f.write("\nFAILURES:\n")
        for e in errors:
            f.write(f"  - {e}\n")
    f.write(f"\n{'ALL TESTS PASSED' if failed == 0 else 'SOME TESTS FAILED'}\n")

print(f"TOTAL: {total}  PASSED: {passed}  FAILED: {failed}")
if errors:
    for e in errors:
        print(f"  FAIL: {e}")
else:
    print("ALL TESTS PASSED")