"""
planner.py — LLM-powered schedule planner for PawPal AI

Takes a pet profile, task list, and retrieved safety rules, builds a
structured prompt, and calls the Google Gemini API (via google-genai)
to generate a natural-language daily schedule with time slots and
safety reasoning.

API key source: GOOGLE_API_KEY in your .env file
Get your free key at: aistudio.google.com
"""

import os
import logging
from typing import List
from google import genai

logger = logging.getLogger(__name__)


def build_prompt(pet_name: str, pet_type: str, breed: str, age: int,
                 weight_lbs: float, health_conditions: List[str],
                 tasks: List[dict], rules_text: str,
                 available_minutes: int = 480) -> str:
    """
    Build the structured prompt sent to the LLM.
    Clearly separates: pet profile, safety rules (RAG), tasks, and format instructions.
    """
    conditions_str = ", ".join(health_conditions) if health_conditions else "None reported"
    tasks_str = "\n".join(
        f"  - {t['name']} ({t['duration']} min, priority: {t['priority']})"
        for t in tasks
    )

    prompt = f"""You are a veterinary-informed pet care scheduling assistant for PawPal.
Your job is to create a safe, practical daily schedule for a pet owner.

=== PET PROFILE ===
Name: {pet_name}
Type: {pet_type}
Breed: {breed if breed else 'Unknown'}
Age: {age} years
Weight: {weight_lbs} lbs
Health conditions: {conditions_str}

=== {rules_text} ===

=== TASKS TO SCHEDULE ===
{tasks_str}

=== INSTRUCTIONS ===
Create a daily schedule starting at 7:00 AM within {available_minutes} minutes total.
You MUST follow all retrieved safety rules above — they override general preferences.
For each task, include:
  - A start time (HH:MM AM/PM format)
  - The task name
  - A one-line safety note explaining why it is scheduled at that time

Format your response EXACTLY like this example (one task per line):
07:00 AM | Feed | Given first so medication can follow with food
07:30 AM | Medication | Administered with breakfast to reduce stomach upset
08:15 AM | Walk | Scheduled 30+ min after feeding to prevent bloat

After the schedule, add one line:
SAFETY SUMMARY: [1-2 sentences summarizing the key safety decisions made]

Do not include any other text outside this format."""

    return prompt


def call_llm(prompt: str, max_retries: int = 3) -> str:
    """
    Call the Google Gemini API with the given prompt.
    Returns the text response. Raises RuntimeError on total failure.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY not set.\n"
            "1. Get your free key at: aistudio.google.com\n"
            "2. Add this line to your .env file:\n"
            "   GOOGLE_API_KEY=your-key-here"
        )

    client = genai.Client(api_key=api_key)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"LLM call attempt {attempt}/{max_retries}")
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            response_text = response.text
            logger.info("LLM call succeeded")
            return response_text

        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"Attempt {attempt} failed: {e}")
            if "api_key" in error_msg or "invalid" in error_msg or "permission" in error_msg:
                raise EnvironmentError(
                    f"API key error: {e}\n"
                    "Check your GOOGLE_API_KEY in the .env file."
                )
            if attempt == max_retries:
                raise RuntimeError(f"LLM call failed after {max_retries} attempts: {e}")

    raise RuntimeError(f"LLM call failed after {max_retries} attempts")


def parse_schedule(llm_response: str) -> List[dict]:
    """
    Parse the LLM's formatted response into a list of schedule entry dicts.
    Each dict: {start_time_str, task_name, safety_note}
    Lines not matching the pipe format are skipped gracefully.
    """
    entries = []
    safety_summary = ""

    for line in llm_response.strip().split("\n"):
        line = line.strip()
        if line.startswith("SAFETY SUMMARY:"):
            safety_summary = line[len("SAFETY SUMMARY:"):].strip()
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                entries.append({
                    "start_time_str": parts[0],
                    "task_name": parts[1],
                    "safety_note": parts[2]
                })
            elif len(parts) == 2:
                entries.append({
                    "start_time_str": parts[0],
                    "task_name": parts[1],
                    "safety_note": ""
                })

    return entries, safety_summary


def generate_schedule(pet_name: str, pet_type: str, breed: str, age: int,
                      weight_lbs: float, health_conditions: List[str],
                      tasks: List[dict], rules_text: str,
                      available_minutes: int = 480) -> tuple:
    """
    Top-level planner function. Builds prompt → calls LLM → parses response.
    Returns (schedule_entries, safety_summary, raw_llm_response).
    """
    prompt = build_prompt(
        pet_name, pet_type, breed, age, weight_lbs,
        health_conditions, tasks, rules_text, available_minutes
    )
    logger.info("Prompt built, calling LLM...")

    raw_response = call_llm(prompt)
    schedule_entries, safety_summary = parse_schedule(raw_response)

    logger.info(f"Parsed {len(schedule_entries)} schedule entries")
    return schedule_entries, safety_summary, raw_response