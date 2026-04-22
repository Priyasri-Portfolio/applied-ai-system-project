"""
agent.py — Agentic pipeline orchestrator for PawPal AI Scheduler

Implements the multi-step agent loop:
  Step 1: Analyze — validate pet profile and task list
  Step 2: Retrieve — search knowledge base for relevant safety rules (RAG)
  Step 3: Plan — call LLM with pet info + rules to generate a schedule
  Step 4: Evaluate — run deterministic safety checks on the schedule
  Step 5: Decide — output schedule if it passes, or retry with violation feedback

Each step prints observable output so the intermediate reasoning is transparent.
"""

import logging
import os
import sys
from typing import List
from dotenv import load_dotenv
load_dotenv()  # reads .env file so GOOGLE_API_KEY is available

from pawpal_system import Pet, Task, Owner, Scheduler, PriorityLevel
from retriever import retrieve_rules, format_rules_for_prompt
from planner import generate_schedule
from evaluator import evaluate_schedule, format_evaluation_result

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pawpal_agent.log", mode="a")
    ]
)
logger = logging.getLogger("agent")

MAX_RETRIES = 3


def _step(num: int, label: str):
    """Print a clearly visible step header for agentic transparency."""
    print(f"\n{'─'*60}")
    print(f"  STEP {num}/4 — {label}")
    print(f"{'─'*60}")


def run_agent(pet: Pet, available_minutes: int = 480) -> dict:
    """
    Run the full agentic pipeline for a single pet.

    Args:
        pet: A Pet object with tasks, health_conditions, breed, etc.
        available_minutes: Total scheduling window in minutes (default 8 hrs)

    Returns:
        result dict with keys: schedule, safety_summary, evaluation, rules_used,
                                passed, violations, attempts
    """
    logger.info(f"Agent starting for pet: {pet.name} ({pet.type}, age {pet.age})")
    print(f"\n{'═'*60}")
    print(f"  🐾 PawPal AI Schedule Generator")
    print(f"  Pet: {pet.name} — {pet.type.title()}, {pet.age} yrs")
    if pet.breed:
        print(f"  Breed: {pet.breed}")
    if pet.health_conditions:
        print(f"  Health conditions: {', '.join(pet.health_conditions)}")
    print(f"{'═'*60}")

    # ── STEP 1: Analyze ────────────────────────────────────────────────────────
    _step(1, "Analyzing pet profile and task list")

    task_dicts = [
        {
            "name": t.name,
            "duration": t.duration,
            "priority": t.priority.name,
        }
        for t in pet.tasks
        if not t.completed
    ]

    if not task_dicts:
        print("  ⚠️  No incomplete tasks found for this pet.")
        logger.warning(f"No tasks for {pet.name}")
        return {"passed": False, "error": "No tasks to schedule"}

    print(f"  Found {len(task_dicts)} task(s) to schedule:")
    for t in task_dicts:
        print(f"    • {t['name']} ({t['duration']} min, {t['priority']} priority)")
    logger.info(f"Step 1 complete: {len(task_dicts)} tasks identified")

    # ── STEP 2: Retrieve (RAG) ─────────────────────────────────────────────────
    _step(2, "Retrieving relevant safety rules (RAG)")

    task_names = [t["name"] for t in task_dicts]
    rules = retrieve_rules(
        pet_type=pet.type,
        age=pet.age,
        health_conditions=pet.health_conditions,
        task_names=task_names,
        breed=pet.breed
    )
    rules_text = format_rules_for_prompt(rules)

    if rules:
        print(f"  Retrieved {len(rules)} relevant safety rule(s):")
        for i, r in enumerate(rules, 1):
            # Truncate long rules for display
            display = r if len(r) <= 90 else r[:87] + "..."
            print(f"    {i}. {display}")
    else:
        print("  No specific rules retrieved — using general best practices.")
    logger.info(f"Step 2 complete: {len(rules)} rules retrieved")

    # ── STEPS 3 & 4: Plan → Evaluate (with retry loop) ────────────────────────
    schedule = []
    safety_summary = ""
    violations = []
    passed = False
    raw_response = ""
    extra_context = ""

    for attempt in range(1, MAX_RETRIES + 1):
        _step(3, f"Generating schedule via LLM (attempt {attempt}/{MAX_RETRIES})")

        # If retrying, inject violation feedback into the rules text
        retry_rules_text = rules_text
        if extra_context:
            retry_rules_text = (
                f"{rules_text}\n\n"
                f"PREVIOUS ATTEMPT VIOLATIONS — MUST FIX:\n{extra_context}"
            )
            print(f"  ⟳ Retrying with violation feedback injected into prompt")

        try:
            schedule, safety_summary, raw_response = generate_schedule(
                pet_name=pet.name,
                pet_type=pet.type,
                breed=pet.breed,
                age=pet.age,
                weight_lbs=pet.weight_lbs,
                health_conditions=pet.health_conditions,
                tasks=task_dicts,
                rules_text=retry_rules_text,
                available_minutes=available_minutes
            )
        except EnvironmentError as e:
            print(f"\n  ❌ Configuration error: {e}")
            logger.error(str(e))
            return {"passed": False, "error": str(e)}
        except RuntimeError as e:
            print(f"\n  ❌ LLM error: {e}")
            logger.error(str(e))
            return {"passed": False, "error": str(e)}

        print(f"  LLM returned {len(schedule)} schedule entry/entries")

        # ── STEP 4: Evaluate ─────────────────────────────────────────────────
        _step(4, "Evaluating schedule against safety guardrails")

        passed, violations = evaluate_schedule(
            schedule=schedule,
            original_tasks=task_dicts,
            pet_type=pet.type,
            age=pet.age,
            health_conditions=pet.health_conditions
        )

        eval_result = format_evaluation_result(passed, violations)
        print(f"  {eval_result}")

        if passed:
            logger.info(f"Schedule passed on attempt {attempt}")
            break
        else:
            # Build violation feedback for next attempt
            extra_context = "\n".join(violations)
            logger.warning(f"Attempt {attempt} failed. Violations:\n{extra_context}")
            if attempt < MAX_RETRIES:
                print(f"\n  Feeding violations back to planner for retry...")

    # ── Output ─────────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    if passed:
        print(f"  ✅ Final Schedule for {pet.name}")
    else:
        print(f"  ⚠️  Best Schedule for {pet.name} (some violations remain after {MAX_RETRIES} attempts)")
    print(f"{'═'*60}")

    for entry in schedule:
        print(f"  {entry['start_time_str']:12s} | {entry['task_name']:<20s} | {entry['safety_note']}")

    if safety_summary:
        print(f"\n  📋 Safety Summary: {safety_summary}")

    if violations:
        print(f"\n  ⚠️  Remaining notes:")
        for v in violations:
            print(f"     {v}")

    print(f"{'═'*60}\n")

    return {
        "pet_name": pet.name,
        "schedule": schedule,
        "safety_summary": safety_summary,
        "rules_used": rules,
        "passed": passed,
        "violations": violations,
        "attempts": attempt,
        "raw_llm_response": raw_response
    }


def run_agent_for_owner(owner: Owner, available_minutes: int = 480) -> List[dict]:
    """Run the agent pipeline for all pets belonging to an owner."""
    results = []
    for pet in owner.pets:
        result = run_agent(pet, available_minutes)
        results.append(result)
    return results
