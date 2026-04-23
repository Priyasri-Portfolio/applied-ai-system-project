"""
evaluator.py — Deterministic guardrail layer for PawPal AI

Validates the LLM-generated schedule against hard safety rules before
it is shown to the user. If violations are found, it returns structured
feedback so the planner can retry with corrected constraints.

This layer is deliberately deterministic — the same input always gives
the same result, providing a reliable safety net regardless of LLM output.
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _time_to_minutes(time_str: str) -> int:
    """
    Convert a time string like '07:30 AM' or '14:00' to minutes-from-midnight.
    Returns -1 if parsing fails.
    """
    time_str = time_str.strip().upper()
    try:
        # Try HH:MM AM/PM
        match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", time_str)
        if not match:
            return -1
        hours, mins = int(match.group(1)), int(match.group(2))
        meridiem = match.group(3)
        if meridiem == "PM" and hours != 12:
            hours += 12
        elif meridiem == "AM" and hours == 12:
            hours = 0
        return hours * 60 + mins
    except Exception:
        return -1


def check_feed_before_exercise(schedule: List[dict], pet_type: str,
                                 health_conditions: List[str]) -> List[str]:
    """
    Rule: Do not schedule vigorous exercise (Walk, Run, Play) within 30 minutes
    of a feeding for dogs. Critical for bloat prevention.
    """
    violations = []
    if pet_type.lower() != "dog":
        return violations

    feed_times = [
        _time_to_minutes(e["start_time_str"])
        for e in schedule
        if "feed" in e["task_name"].lower() or "meal" in e["task_name"].lower()
    ]
    exercise_tasks = [
        e for e in schedule
        if any(word in e["task_name"].lower() for word in ["walk", "run", "play", "exercise"])
    ]

    for ex in exercise_tasks:
        ex_time = _time_to_minutes(ex["start_time_str"])
        if ex_time < 0:
            continue
        for ft in feed_times:
            if ft < 0:
                continue
            gap = ex_time - ft
            if 0 < gap < 30:
                violations.append(
                    f"VIOLATION: '{ex['task_name']}' scheduled only {gap} min after feeding. "
                    f"Dogs need 30+ min gap to prevent bloat. Move '{ex['task_name']}' "
                    f"to at least {_minutes_to_time(ft + 30)}."
                )

    return violations


def check_exercise_duration(schedule: List[dict], pet_type: str,
                              age: int, health_conditions: List[str]) -> List[str]:
    """
    Rule: Senior dogs (7+) should not have exercise tasks over 30 min.
    Dogs with heart conditions: max 15 min. Hip dysplasia: max 20 min.
    """
    violations = []
    if pet_type.lower() != "dog":
        return violations

    conditions_lower = [c.lower() for c in health_conditions]
    is_senior = age >= 7
    has_heart = any("heart" in c or "cardiac" in c for c in conditions_lower)
    has_hip = any("hip" in c or "dysplasia" in c for c in conditions_lower)

    for entry in schedule:
        task_name = entry["task_name"].lower()
        if not any(w in task_name for w in ["walk", "run", "exercise", "play"]):
            continue
        duration = entry.get("duration_min", 0)
        if duration == 0:
            continue  # Can't check without duration

        if has_heart and duration > 15:
            violations.append(
                f"VIOLATION: '{entry['task_name']}' is {duration} min. "
                f"Dogs with heart conditions should not exceed 15 min of exercise."
            )
        elif has_hip and duration > 20:
            violations.append(
                f"VIOLATION: '{entry['task_name']}' is {duration} min. "
                f"Dogs with hip dysplasia should not exceed 20 min of exercise."
            )
        elif is_senior and duration > 30:
            violations.append(
                f"VIOLATION: '{entry['task_name']}' is {duration} min. "
                f"Senior dogs (7+) should limit exercise to 30 min."
            )

    return violations


def check_medication_with_food(schedule: List[dict]) -> List[str]:
    """
    Rule: Medication should be scheduled within 30 minutes AFTER a feeding,
    not on an empty stomach.
    """
    violations = []

    med_tasks = [
        e for e in schedule
        if any(w in e["task_name"].lower() for w in ["medication", "medicine", "pill", "dose"])
    ]
    feed_times = [
        _time_to_minutes(e["start_time_str"])
        for e in schedule
        if "feed" in e["task_name"].lower() or "meal" in e["task_name"].lower()
    ]

    for med in med_tasks:
        med_time = _time_to_minutes(med["start_time_str"])
        if med_time < 0:
            continue
        # Check if there's a meal within 45 min before or after
        near_food = any(
            abs(med_time - ft) <= 45
            for ft in feed_times
            if ft >= 0
        )
        if not near_food and feed_times:
            violations.append(
                f"CAUTION: '{med['task_name']}' appears not to be scheduled near a meal. "
                f"Consider pairing with feeding to reduce stomach upset."
            )

    return violations


def check_schedule_not_empty(schedule: List[dict], original_tasks: List[dict]) -> List[str]:
    """Guardrail: LLM must produce at least one scheduled entry per original task."""
    violations = []
    if not schedule:
        violations.append("VIOLATION: LLM returned an empty schedule. No tasks were planned.")
        return violations

    scheduled_names = {e["task_name"].lower() for e in schedule}
    for task in original_tasks:
        if task["name"].lower() not in scheduled_names:
            violations.append(
                f"MISSING: Task '{task['name']}' was not included in the generated schedule."
            )
    return violations


def _minutes_to_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    meridiem = "AM" if hours < 12 else "PM"
    display_hour = hours if hours <= 12 else hours - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour:02d}:{mins:02d} {meridiem}"


def evaluate_schedule(schedule: List[dict], original_tasks: List[dict],
                       pet_type: str, age: int,
                       health_conditions: List[str]) -> Tuple[bool, List[str]]:
    """
    Run all guardrail checks against a generated schedule.

    Returns:
        passed (bool): True if no violations found
        violations (List[str]): List of violation/caution messages
    """
    all_violations = []

    all_violations += check_schedule_not_empty(schedule, original_tasks)
    all_violations += check_feed_before_exercise(schedule, pet_type, health_conditions)
    all_violations += check_exercise_duration(schedule, pet_type, age, health_conditions)
    all_violations += check_medication_with_food(schedule)

    passed = not any(v.startswith("VIOLATION") or v.startswith("MISSING") for v in all_violations)

    if passed and not all_violations:
        logger.info("Evaluator: schedule passed all checks")
    elif passed and all_violations:
        logger.info(f"Evaluator: schedule passed with {len(all_violations)} caution(s)")
    else:
        logger.warning(f"Evaluator: schedule FAILED with {len(all_violations)} violation(s)")

    return passed, all_violations


def format_evaluation_result(passed: bool, violations: List[str]) -> str:
    """Return a human-readable evaluation result string."""
    if passed and not violations:
        return "✅ All safety checks passed."
    elif passed:
        lines = ["⚠️  Schedule passed with cautions:"]
        lines += [f"   {v}" for v in violations]
        return "\n".join(lines)
    else:
        lines = ["❌ Schedule failed safety checks:"]
        lines += [f"   {v}" for v in violations]
        return "\n".join(lines)
