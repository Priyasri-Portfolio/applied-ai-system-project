from dataclasses import dataclass, field
from typing import List
from datetime import datetime, timedelta, date  # NEW IMPORTS FOR RECURRING TASKS AND HH:MM SORTING
from collections import namedtuple
from enum import Enum
import heapq
import json
import os
from datetime import date


class PriorityLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class Owner:
    def __init__(self, name):
        self.name = name
        self.pets = []

    def add_pet(self, pet):
        self.pets.append(pet)

    # -----------------------------------------
    # Add your persistence methods *here*
    # -----------------------------------------

    def to_dict(self):
        return {
            "name": self.name,
            "pets": [pet.to_dict() for pet in self.pets]
        }

    def save_to_json(self, filepath="data.json"):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @staticmethod
    def load_from_json(filepath="data.json"):
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r") as f:
            data = json.load(f)

        owner = Owner(data["name"])
        for p in data["pets"]:
            owner.add_pet(Pet.from_dict(p))

        return owner


@dataclass
class Pet:
    name: str
    type: str
    age: int
    tasks: List['Task'] = field(default_factory=list)
    health_conditions: List[str] = field(default_factory=list)
    breed: str = ""
    weight_lbs: float = 0.0
    
    def __post_init__(self):
        """Validate pet attributes after initialization."""
        #1)step 5)added after asking copilot to check on the skeleton, initially not added
        if self.age < 0:
            raise ValueError("Age must be non-negative")
    #2)step1)
    def add_task(self, task: 'Task'):
        """Add a task to the pet's list of tasks."""
        self.tasks.append(task)

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "age": self.age,
            "tasks": [task.to_dict() for task in self.tasks]
        }

    @staticmethod
    def from_dict(data):
        pet = Pet(data["name"], data["type"], data["age"])
        for t in data["tasks"]:
            pet.add_task(Task.from_dict(t))
        return pet


@dataclass
class Task:
    name: str
    duration: int
    priority: PriorityLevel
    frequency: str = "daily"
    due_date: date = None  # Optional due date for scheduling
    completed: bool = False
    def next_due_date(self):
        """Return the next due date based on frequency."""
        freq = self.frequency.lower()

        if freq == "daily":
            return self.due_date + timedelta(days=1)
        elif freq == "weekly":
            return self.due_date + timedelta(weeks=1)
        else:
            return None

    def __post_init__(self):
        """Validate task attributes after initialization."""
        if self.duration <= 0:
            raise ValueError("Duration must be positive")
        if self.due_date is None:
            self.due_date = datetime.now().date()
    #Stateful method
    def mark_complete(self):
        """Mark this task as completed."""
        self.completed = True

    def __str__(self):
        status = "✓" if self.completed else "✗"
        return f"{self.name} ({self.duration} min, priority {self.priority.name}, {status})"

    def to_dict(self):
        return {
            "name": self.name,
            "duration": self.duration,
            "priority": self.priority,
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed
        }

@staticmethod
def from_dict(data):
    task = Task(
        name=data["name"],
        duration=data["duration"],
        priority=data["priority"],
        frequency=data.get("frequency"),
        due_date=date.fromisoformat(data["due_date"]) if data["due_date"] else None
    )
    task.completed = data.get("completed", False)
    return task


#1)step 5)this class was modeified after asked copilot to check on the skeleton.
class Scheduler:
    """Generates a prioritized schedule of pet tasks for an owner."""

    def __init__(self, owner: Owner):
        """Initialize the scheduler with an owner."""
        self.owner = owner

    TaskPet = namedtuple('TaskPet', ['task', 'pet'])

    def _get_all_tasks(self) -> List[Task]:
        """Collect all tasks from the owner's pets."""
        all_tasks = []
        for pet in self.owner.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    # NEW: Get all tasks with pet information - IMPLEMENTED (helper for filtering)
    def _get_task_pets(self):
        """Collect all tasks with associated pet information as TaskPet namedtuples."""
        for pet in self.owner.pets:
            for task in pet.tasks:
                yield self.TaskPet(task, pet)

    def sort_tasks_by_priority(self):
        """Sort tasks by priority (higher first)."""
        self.tasks.sort(key=lambda t: t.priority.value, reverse=True)

    def generate_plan(self, available_time: int) -> List[Task]:
        """Return a list of tasks that fit within the available time, prioritized by priority then duration."""
        #change made on Phase 4,step 5
        #tasks = getattr(self, "tasks", self._get_all_tasks())

        tasks = self._get_all_tasks()
        # Use heapq for efficient priority selection: higher priority first, then shorter duration first
        heap = [(-t.priority.value, t.duration, t) for t in tasks]
        heapq.heapify(heap)
        plan = []
        total_time = 0
        while heap and total_time < available_time:
            _, _, task = heapq.heappop(heap)
            if total_time + task.duration <= available_time:
                plan.append(task)
                total_time += task.duration
        return plan

    # NEW: Sorting tasks by time (duration) - IMPLEMENTED
    #chnage made on Phase 4) step 5
    def sort_tasks_by_time(self, ascending=True) -> List[Task]:
        """Sort tasks by duration (time required). Default: shortest first."""
        tasks = self._get_all_tasks()
        return sorted(tasks, key=lambda t: t.duration, reverse=not ascending)

    # NEW: Sort tasks with a time string key field in dicts (using datetime parsing) - IMPLEMENTED
    def sort_tasks_by_start_time_str(self, scheduled_tasks: List[dict], start_key: str = 'start_time_str') -> List[dict]:
        """Sort a list of task dicts by HH:MM string in a specified key."""
        from datetime import datetime

        return sorted(
            scheduled_tasks,
            key=lambda t: datetime.strptime(t.get(start_key, '00:00'), '%H:%M')
        )

    # NEW: Filtering tasks by pet name - IMPLEMENTED
    def filter_tasks_by_pet(self, pet_name: str) -> List:
        """Filter tasks to show only those for a specific pet. Returns list of TaskPet namedtuples."""
        return [tp for tp in self._get_task_pets() if tp.pet.name == pet_name]

    # NEW: Filtering tasks by completion status - IMPLEMENTED
    def filter_tasks_by_status(self, completed: bool = False) -> List:
        """Filter tasks by completion status. Default: show incomplete tasks. Returns list of TaskPet namedtuples."""
        return [tp for tp in self._get_task_pets() if tp.task.completed == completed]

    # NEW: Filtering tasks by completion status or pet name - IMPLEMENTED
    def filter_tasks(self, completed: bool = None, pet_name: str = None) -> List:
        """Filter tasks by completion status and/or pet name. If both are provided, both conditions are applied."""
        return [tp for tp in self._get_task_pets() 
                if (completed is None or tp.task.completed == completed) and
                   (pet_name is None or tp.pet.name == pet_name)]

    # NEW: Handling recurring tasks - generate instances for multiple days - IMPLEMENTED
    def generate_recurring_instances(self, days_ahead: int = 7):
        """Generate task instances for recurring tasks over specified days ahead."""
        today = datetime.now().date()
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.frequency == "daily":
                    for i in range(days_ahead):
                        yield {
                            'task': task,
                            'pet': pet,
                            'date': today + timedelta(days=i),
                            'scheduled_time': None  # To be set by scheduler
                        }
                elif task.frequency == "weekly":
                    for i in range(0, days_ahead, 7):
                        yield {
                            'task': task,
                            'pet': pet,
                            'date': today + timedelta(days=i),
                            'scheduled_time': None
                        }

    # NEW: Basic conflict detection - check for time overlaps - IMPLEMENTED
    def detect_time_conflicts(self, scheduled_tasks: List[dict]) -> List[dict]:
        """Detect overlapping tasks in a schedule. Assumes scheduled_tasks is sorted by 'start_time'."""
        conflicts = []
        for i in range(len(scheduled_tasks) - 1):
            curr = scheduled_tasks[i]
            nxt = scheduled_tasks[i + 1]
            curr_end = curr.get('start_time', 0) + curr['task'].duration
            nxt_start = nxt.get('start_time', 0)
            if curr_end > nxt_start:
                conflicts.append({
                    'task1': curr['task'],
                    'task2': nxt['task'],
                    'overlap_minutes': curr_end - nxt_start,
                    'pet1': curr.get('pet', 'Unknown'),
                    'pet2': nxt.get('pet', 'Unknown')
                })
        return conflicts

    def check_for_conflicts(self, scheduled_tasks: List[dict]) -> str:
        """Detect overlapping tasks and return a warning message."""
        conflicts = self.detect_time_conflicts(scheduled_tasks)

        if not conflicts:
            return "No conflicts detected."

        lines = ["WARNING: Task conflicts detected:"]
        for c in conflicts:
            task1 = c['task1']
            task2 = c['task2']
            overlap = c['overlap_minutes']
            pet1 = getattr(c.get('pet1'), 'name', 'Unknown')
            pet2 = getattr(c.get('pet2'), 'name', 'Unknown')
            lines.append(
                f"- {task1.name} (pet: {pet1}) overlaps with {task2.name} (pet: {pet2}) by {overlap} minutes"
            )

        return "\n".join(lines)

    #Phase 4)step 4) adding a lightweight wrapper method
    # NEW: mark a recurring task complete, add next instance automatically - IMPLEMENTED
    def mark_task_complete(self, pet: 'Pet', task: 'Task') -> bool:
        """Mark a task complete and create a new task for the next recurrence if daily/weekly."""
        if task not in pet.tasks:
            raise ValueError("Task does not belong to this pet")

        # Mark current task complete
        task.mark_complete()

        # Only create a new instance for recurring tasks
        next_date = task.next_due_date()
        if next_date is None:
            return False

        # Create a fresh task instance for next recurrence
        new_task = Task(
            name=task.name,
            duration=task.duration,
            priority=task.priority,
            frequency=task.frequency,
            due_date=next_date,
            completed=False
        )
        pet.add_task(new_task)

        return True

