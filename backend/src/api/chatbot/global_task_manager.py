"""
Global task manager - now simplified to just export the Task class.
The actual database operations are handled by the DatabaseTaskManager.
"""

from dataclasses import dataclass


@dataclass
class Task:
    id: int
    title: str
    completed: bool = False