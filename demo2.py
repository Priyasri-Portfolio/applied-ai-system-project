import os
from dotenv import load_dotenv
load_dotenv()
from pawpal_system import Pet, Task, PriorityLevel
from agent import run_agent

pet = Pet(
    name="Max",
    type="dog",
    age=10,
    breed="Bulldog",
    weight_lbs=50.0,
    health_conditions=["heart condition"]
)
pet.add_task(Task("Feed",       10, PriorityLevel.HIGH))
pet.add_task(Task("Medication",  5, PriorityLevel.HIGH))
pet.add_task(Task("Walk",       30, PriorityLevel.MEDIUM))

result = run_agent(pet, available_minutes=240)