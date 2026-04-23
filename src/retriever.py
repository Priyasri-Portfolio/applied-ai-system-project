"""
retriever.py — RAG module for PawPal AI Scheduler

Searches the pet care knowledge base (data/pet_care_rules.txt) for rules
that are relevant to a given pet profile. Injects retrieved rules into the
LLM prompt so every schedule is grounded in veterinary-informed guidelines.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "Data", "petcare_rules.txt")


def load_rules(filepath: str = KNOWLEDGE_BASE_PATH) -> List[dict]:
    """
    Parse the knowledge base text file into a list of rule dicts.
    Each rule dict has: text, applies_to (list), keywords (list).
    """
    rules = []
    if not os.path.exists(filepath):
        logger.error(f"Knowledge base not found at: {filepath}")
        return rules

    with open(filepath, "r") as f:
        lines = f.readlines()

    current_rule = None
    for line in lines:
        line = line.strip()
        if line.startswith("rule:"):
            current_rule = {
                "text": line[len("rule:"):].strip(),
                "applies_to": [],
                "keywords": []
            }
            rules.append(current_rule)
        elif line.startswith("applies_to:") and current_rule:
            current_rule["applies_to"] = [s.strip() for s in line[len("applies_to:"):].split(",")]
        elif line.startswith("keywords:") and current_rule:
            current_rule["keywords"] = [s.strip() for s in line[len("keywords:"):].split(",")]

    logger.info(f"Loaded {len(rules)} rules from knowledge base")
    return rules


def retrieve_rules(pet_type: str, age: int, health_conditions: List[str],
                   task_names: List[str], breed: str = "") -> List[str]:
    """
    Retrieve relevant rules from the knowledge base for a given pet profile.

    Matching logic:
    1. Species match — rule's applies_to includes the pet type (or is general)
    2. Keyword match — any keyword in the rule matches pet details or task names

    Returns a deduplicated list of rule text strings.
    """
    rules = load_rules()
    matched_texts = []
    seen = set()

    # Build a combined search string from all pet details
    search_terms = [pet_type.lower(), breed.lower()]
    search_terms += [c.lower() for c in health_conditions]
    search_terms += [t.lower() for t in task_names]

    # Senior age keywords
    if (pet_type.lower() == "dog" and age >= 7) or (pet_type.lower() == "cat" and age >= 10):
        search_terms.append("senior")
    if age < 1:
        search_terms.append("puppy")

    for rule in rules:
        # Check species applicability
        species_ok = (
            pet_type.lower() in rule["applies_to"] or
            not rule["applies_to"]  # empty = general
        )
        if not species_ok:
            continue

        # Check keyword overlap
        rule_keywords = [k.lower() for k in rule["keywords"]]
        matched = any(
            term in kw or kw in term
            for term in search_terms
            for kw in rule_keywords
        )

        if matched and rule["text"] not in seen:
            matched_texts.append(rule["text"])
            seen.add(rule["text"])

    logger.info(
        f"Retrieved {len(matched_texts)} rules for {pet_type} '{breed}' "
        f"age={age}, conditions={health_conditions}, tasks={task_names}"
    )
    return matched_texts


def format_rules_for_prompt(rules: List[str]) -> str:
    """Format retrieved rules as a numbered list for injection into the LLM prompt."""
    if not rules:
        return "No specific safety rules retrieved. Use general best practices."
    lines = ["RETRIEVED SAFETY RULES (must be respected in the schedule):"]
    for i, rule in enumerate(rules, 1):
        lines.append(f"  {i}. {rule}")
    return "\n".join(lines)