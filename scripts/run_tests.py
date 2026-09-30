import unittest
import sys
import json
import os
import time

def run_test_suite():
    print("=" * 60)
    print("ONLINE VOTING SYSTEM - AUTOMATED TEST EXECUTION")
    print("=" * 60)

    # Load test suite from test_app.py
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='.', pattern='test_app.py')

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = round(time.time() - start_time, 3)

    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - (failures + errors)

    summary = {
        "total": total_tests,
        "passed": passed,
        "failed": failures,
        "errors": errors,
        "duration_seconds": duration,
        "is_successful": result.wasSuccessful()
    }

    # Save summary to json file for pipeline and dashboard
    os.makedirs("test-reports", exist_ok=True)
    with open(os.path.join("test-reports", "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed}/{total_tests} PASSED ({duration}s)")
    if failures > 0 or errors > 0:
        print(f"FAILURES: {failures}, ERRORS: {errors}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)

if __name__ == '__main__':
    run_test_suite()
