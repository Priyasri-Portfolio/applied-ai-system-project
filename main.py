"""
main.py — PawPal AI Scheduler demo

Demonstrates the full agentic pipeline on 3 pet profiles:
  1. Bella — healthy dog, standard schedule
  2. Max — senior Bulldog with a heart condition (guardrail triggered)
  3. Whiskers — senior arthritic cat

Run with:
    python main.py

Requires GOOGLE_API_KEY in your .env file.
Get a free key at: aistudio.google.com
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()  # reads GOOGLE_API_KEY from .env file
from pawpal_system import Owner, Pet, Task, PriorityLevel
from agent import run_agent


def demo_1_healthy_dog():
    """Example 1: Standard healthy dog — all checks should pass."""
    print("\n" + "█"*60)
    print("  DEMO 1 — Bella, healthy Golden Retriever")
    print("█"*60)

    pet = Pet(
        name="Bella",
        type="dog",
        age=3,
        breed="Golden Retriever",
        weight_lbs=65.0,
        health_conditions=[]
    )
    pet.add_task(Task("Feed",       10, PriorityLevel.HIGH))
    pet.add_task(Task("Medication", 5,  PriorityLevel.HIGH))
    pet.add_task(Task("Morning Walk", 30, PriorityLevel.MEDIUM))
    pet.add_task(Task("Groom",      20, PriorityLevel.LOW))
    pet.add_task(Task("Evening Walk", 20, PriorityLevel.MEDIUM))

    return run_agent(pet, available_minutes=480)


def demo_2_dog_with_heart_condition():
    """Example 2: Senior Bulldog with heart condition — guardrail should flag long exercise."""
    print("\n" + "█"*60)
    print("  DEMO 2 — Max, Bulldog with heart condition")
    print("█"*60)

    pet = Pet(
        name="Max",
        type="dog",
        age=10,
        breed="Bulldog",
        weight_lbs=50.0,
        health_conditions=["heart condition"]
    )
    pet.add_task(Task("Feed",        10, PriorityLevel.HIGH))
    pet.add_task(Task("Medication",  5,  PriorityLevel.HIGH))
    pet.add_task(Task("Walk",        30, PriorityLevel.MEDIUM))  # Should be reduced by LLM

    return run_agent(pet, available_minutes=240)


def demo_3_senior_cat():
    """Example 3: Senior arthritic cat — age-specific rules applied."""
    print("\n" + "█"*60)
    print("  DEMO 3 — Whiskers, senior Persian cat with arthritis")
    print("█"*60)

    pet = Pet(
        name="Whiskers",
        type="cat",
        age=14,
        breed="Persian",
        weight_lbs=9.0,
        health_conditions=["arthritis"]
    )
    pet.add_task(Task("Feed",         10, PriorityLevel.HIGH))
    pet.add_task(Task("Medication",    5, PriorityLevel.HIGH))
    pet.add_task(Task("Gentle Play",  15, PriorityLevel.MEDIUM))
    pet.add_task(Task("Groom",        20, PriorityLevel.LOW))

    return run_agent(pet, available_minutes=360)


def print_summary(results: list):
    """Print a final pass/fail summary across all demos."""
    print("\n" + "═"*60)
    print("  FINAL SUMMARY")
    print("═"*60)
    for r in results:
        if "error" in r:
            status = "❌ ERROR"
        elif r.get("passed"):
            status = "✅ PASSED"
        else:
            status = "⚠️  PARTIAL"
        pet = r.get("pet_name", "Unknown")
        attempts = r.get("attempts", "—")
        rules = len(r.get("rules_used", []))
        print(f"  {pet:<12} {status}   {attempts} attempt(s)   {rules} rule(s) applied")
    print("═"*60 + "\n")


if __name__ == "__main__":
    # Check API key before running anything
    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n❌ GOOGLE_API_KEY not set.")
        print("   1. Get your free key at: aistudio.google.com")
        print("   2. Add this to your .env file:  GOOGLE_API_KEY=your-key-here")
        sys.exit(1)

    results = []
    results.append(demo_1_healthy_dog())
    results.append(demo_2_dog_with_heart_condition())
    results.append(demo_3_senior_cat())
    print_summary(results)