"""
test_evaluator.py — Test harness for PawPal AI (Stretch Feature)

Runs the evaluator guardrails against a set of predefined scenarios
and prints a pass/fail summary table.

These tests do NOT call the LLM — they test the deterministic
evaluator layer directly, which is fast and reproducible.

Run with:
    python test_evaluator.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluator import evaluate_schedule, format_evaluation_result

# ── Test case definitions ───────────────────────────────────────────────────

TEST_CASES = [
    {
        "id": "TC-01",
        "description": "Healthy dog — valid schedule, all checks should pass",
        "schedule": [
            {"start_time_str": "07:00 AM", "task_name": "Feed",         "safety_note": ""},
            {"start_time_str": "07:30 AM", "task_name": "Medication",   "safety_note": ""},
            {"start_time_str": "08:15 AM", "task_name": "Morning Walk", "safety_note": "", "duration_min": 30},
            {"start_time_str": "05:30 PM", "task_name": "Evening Walk", "safety_note": "", "duration_min": 20},
        ],
        "original_tasks": [
            {"name": "Feed"}, {"name": "Medication"},
            {"name": "Morning Walk"}, {"name": "Evening Walk"}
        ],
        "pet_type": "dog",
        "age": 3,
        "health_conditions": [],
        "expect_pass": True,
        "expect_violations_containing": []
    },
    {
        "id": "TC-02",
        "description": "Dog fed then walked 10 min later — bloat risk violation",
        "schedule": [
            {"start_time_str": "07:00 AM", "task_name": "Feed", "safety_note": ""},
            {"start_time_str": "07:10 AM", "task_name": "Walk", "safety_note": "", "duration_min": 20},
        ],
        "original_tasks": [{"name": "Feed"}, {"name": "Walk"}],
        "pet_type": "dog",
        "age": 4,
        "health_conditions": [],
        "expect_pass": False,
        "expect_violations_containing": ["bloat"]
    },
    {
        "id": "TC-03",
        "description": "Dog with heart condition — long walk should violate",
        "schedule": [
            {"start_time_str": "07:00 AM", "task_name": "Feed",     "safety_note": ""},
            {"start_time_str": "08:00 AM", "task_name": "Walk",     "safety_note": "", "duration_min": 30},
        ],
        "original_tasks": [{"name": "Feed"}, {"name": "Walk"}],
        "pet_type": "dog",
        "age": 10,
        "health_conditions": ["heart condition"],
        "expect_pass": False,
        "expect_violations_containing": ["heart"]
    },
    {
        "id": "TC-04",
        "description": "Senior dog — 20 min walk should pass (under 30 min limit)",
        "schedule": [
            {"start_time_str": "07:00 AM", "task_name": "Feed",  "safety_note": ""},
            {"start_time_str": "08:00 AM", "task_name": "Walk",  "safety_note": "", "duration_min": 20},
        ],
        "original_tasks": [{"name": "Feed"}, {"name": "Walk"}],
        "pet_type": "dog",
        "age": 8,
        "health_conditions": [],
        "expect_pass": True,
        "expect_violations_containing": []
    },
    {
        "id": "TC-05",
        "description": "Empty schedule — should flag VIOLATION",
        "schedule": [],
        "original_tasks": [{"name": "Feed"}, {"name": "Walk"}],
        "pet_type": "dog",
        "age": 3,
        "health_conditions": [],
        "expect_pass": False,
        "expect_violations_containing": ["empty"]
    },
    {
        "id": "TC-06",
        "description": "Cat schedule — feed + medication close together, should pass",
        "schedule": [
            {"start_time_str": "07:30 AM", "task_name": "Feed",       "safety_note": ""},
            {"start_time_str": "07:35 AM", "task_name": "Medication", "safety_note": ""},
            {"start_time_str": "10:00 AM", "task_name": "Gentle Play","safety_note": "", "duration_min": 10},
        ],
        "original_tasks": [
            {"name": "Feed"}, {"name": "Medication"}, {"name": "Gentle Play"}
        ],
        "pet_type": "cat",
        "age": 14,
        "health_conditions": ["arthritis"],
        "expect_pass": True,
        "expect_violations_containing": []
    },
    {
        "id": "TC-07",
        "description": "Dog with hip dysplasia — 25 min walk should violate",
        "schedule": [
            {"start_time_str": "07:00 AM", "task_name": "Feed", "safety_note": ""},
            {"start_time_str": "08:00 AM", "task_name": "Walk", "safety_note": "", "duration_min": 25},
        ],
        "original_tasks": [{"name": "Feed"}, {"name": "Walk"}],
        "pet_type": "dog",
        "age": 6,
        "health_conditions": ["hip dysplasia"],
        "expect_pass": False,
        "expect_violations_containing": ["dysplasia"]
    },
    {
        "id": "TC-08",
        "description": "Missing task in schedule — LLM forgot to include Groom",
        "schedule": [
            {"start_time_str": "07:00 AM", "task_name": "Feed",  "safety_note": ""},
            {"start_time_str": "08:00 AM", "task_name": "Walk",  "safety_note": "", "duration_min": 20},
        ],
        "original_tasks": [{"name": "Feed"}, {"name": "Walk"}, {"name": "Groom"}],
        "pet_type": "dog",
        "age": 4,
        "health_conditions": [],
        "expect_pass": False,
        "expect_violations_containing": ["Groom"]
    },
]


# ── Test runner ─────────────────────────────────────────────────────────────

def run_tests():
    print("\n" + "═"*65)
    print("  PawPal AI — Evaluator Test Harness")
    print("═"*65)
    print(f"  {'ID':<8} {'Result':<8} {'Expected':<10} {'Description'}")
    print(f"  {'─'*7} {'─'*7} {'─'*9} {'─'*38}")

    passed_count = 0
    failed_count = 0
    results = []

    for tc in TEST_CASES:
        passed, violations = evaluate_schedule(
            schedule=tc["schedule"],
            original_tasks=tc["original_tasks"],
            pet_type=tc["pet_type"],
            age=tc["age"],
            health_conditions=tc["health_conditions"]
        )

        # Check violations contain expected keywords
        violation_text = " ".join(violations).lower()
        keyword_ok = all(
            kw.lower() in violation_text
            for kw in tc["expect_violations_containing"]
        )

        test_passed = (passed == tc["expect_pass"]) and keyword_ok

        status = "✅ PASS" if test_passed else "❌ FAIL"
        expected = "pass" if tc["expect_pass"] else "fail"

        print(f"  {tc['id']:<8} {status:<8} {expected:<10} {tc['description']}")

        if not test_passed:
            print(f"           → Got passed={passed}, violations={violations}")
            failed_count += 1
        else:
            passed_count += 1

        results.append({
            "id": tc["id"],
            "test_passed": test_passed,
            "eval_passed": passed,
            "violations": violations
        })

    print("═"*65)
    total = len(TEST_CASES)
    print(f"  Results: {passed_count}/{total} tests passed", end="")
    if failed_count > 0:
        print(f"  ({failed_count} failed)")
    else:
        print("  — All tests passed ✅")
    print("═"*65 + "\n")

    return passed_count, failed_count


if __name__ == "__main__":
    run_tests()