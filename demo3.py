import os
from dotenv import load_dotenv
load_dotenv()
from pawpal_system import Pet, Task, PriorityLevel
from agent import run_agent

pet = Pet(
    name="Whiskers",
    type="cat",
    age=14,
    breed="Persian",
    weight_lbs=9.0,
    health_conditions=["arthritis"]
)
pet.add_task(Task("Feed",        10, PriorityLevel.HIGH))
pet.add_task(Task("Medication",   5, PriorityLevel.HIGH))
pet.add_task(Task("Gentle Play", 15, PriorityLevel.MEDIUM))
pet.add_task(Task("Groom",       20, PriorityLevel.LOW))

result = run_agent(pet, available_minutes=360)