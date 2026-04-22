import os, sys
from dotenv import load_dotenv
load_dotenv()
from pawpal_system import Pet, Task, PriorityLevel
from agent import run_agent

pet = Pet(
    name="Bella",
    type="dog",
    age=3,
    breed="Golden Retriever",
    weight_lbs=65.0,
    health_conditions=[]
)
pet.add_task(Task("Feed",         10, PriorityLevel.HIGH))
pet.add_task(Task("Medication",    5, PriorityLevel.HIGH))
pet.add_task(Task("Morning Walk", 30, PriorityLevel.MEDIUM))
pet.add_task(Task("Groom",        20, PriorityLevel.LOW))
pet.add_task(Task("Evening Walk", 20, PriorityLevel.MEDIUM))

result = run_agent(pet, available_minutes=480)