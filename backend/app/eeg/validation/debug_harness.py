import json
from app.eeg.validation.validation_harness import ValidationHarness
from app.eeg.validation.benchmark_registry import CORE_BENCHMARKS

def debug_failures():
    harness = ValidationHarness()
    suite_result = harness.run_full_suite()
    
    print(f"\nSuite Pass Rate: {suite_result.overall_pass_rate*100:.1f}%")
    
    for res in suite_result.results:
        print(f"\nBenchmark: {res.benchmark_id}")
        print(f"Status: {res.status}")
        print(f"Pass Overall: {res.pass_overall}")
        if res.critical_failures:
            print(f"Critical Failures: {res.critical_failures}")
        
        for layer, score in res.layer_scores.items():
            print(f"  Layer: {layer} | Status: {score.status} | Score: {score.score:.2f}")
            for detail in score.details:
                print(f"    - {detail}")

if __name__ == "__main__":
    debug_failures()
