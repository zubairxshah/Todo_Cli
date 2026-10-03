"""
Task operations module for the backend API.
This handles direct task operations using the database instead of in-memory storage.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException
import re
from dataclasses import dataclass
from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime
import uuid

# Import database components using relative imports
try:
    from ...database import get_session, engine
    from ...models.task import Task as DBTask
except ImportError:
    from database import get_session, engine
    from models.task import Task as DBTask


@dataclass
class Task:
    id: int
    title: str
    completed: bool = False


class DatabaseTaskManager:
    """
    Manager that handles task operations using the database backend.
    """
    def __init__(self):
        # Use a dummy user_id for non-authenticated tasks
        self.default_user_id = uuid.uuid4()

    def _convert_int_to_uuid(self, int_id: int) -> UUID:
        """Convert an integer ID back to the original UUID."""
        # Since we convert UUID to int by taking first 8 hex chars, we need to find the matching UUID
        # by getting all tasks and matching the converted ID
        session = self._get_session()
        try:
            statement = select(DBTask).where(DBTask.user_id == self.default_user_id)
            db_tasks = session.exec(statement).all()

            for db_task in db_tasks:
                task_id = int(str(db_task.id)[:8], 16) if str(db_task.id) else hash(db_task.title) % 10000
                if task_id == int_id:
                    return db_task.id
        finally:
            session.close()

        # If not found, return None to indicate the task doesn't exist
        return None

    def _get_session(self):
        """Get a database session."""
        return Session(engine)

    def add_task(self, title: str):
        """Add a task to the database."""
        if not title or not title.strip():
            return None

        session = self._get_session()
        try:
            # Create a new task with a default user_id (for non-authenticated tasks)
            db_task = DBTask(
                title=title.strip(),
                description=None,
                completed=False,
                user_id=self.default_user_id
            )
            session.add(db_task)
            session.commit()
            session.refresh(db_task)

            # Convert DBTask ID to int for compatibility with our interface
            # Use first 8 hex chars of UUID to create an integer ID
            task_id = int(str(db_task.id)[:8], 16) if str(db_task.id) else hash(title) % 10000
            internal_task = Task(
                id=task_id,
                title=db_task.title,
                completed=db_task.completed
            )
            return internal_task
        except Exception as e:
            print(f"Error adding task to database: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_all_tasks(self):
        """Get all tasks from the database."""
        session = self._get_session()
        try:
            # Get tasks for the default user
            statement = select(DBTask).where(DBTask.user_id == self.default_user_id)
            db_tasks = session.exec(statement).all()

            # Convert DBTask objects to internal Task objects
            internal_tasks = []
            for db_task in db_tasks:
                task_id = int(str(db_task.id)[:8], 16) if str(db_task.id) else hash(db_task.title) % 10000
                internal_task = Task(
                    id=task_id,
                    title=db_task.title,
                    completed=db_task.completed
                )
                internal_tasks.append(internal_task)
            return internal_tasks
        except Exception as e:
            print(f"Error getting tasks from database: {e}")
            return []
        finally:
            session.close()

    def get_task_by_id(self, task_id: int):
        """Get a specific task by ID from the database."""
        session = self._get_session()
        try:
            # Convert the task_id back to the original UUID
            db_task_uuid = self._convert_int_to_uuid(task_id)

            # Get the actual DB record using the UUID and user_id
            statement = select(DBTask).where(
                DBTask.id == db_task_uuid,
                DBTask.user_id == self.default_user_id
            )
            db_task = session.exec(statement).first()

            if db_task:
                task_id = int(str(db_task.id)[:8], 16) if str(db_task.id) else hash(db_task.title) % 10000
                return Task(
                    id=task_id,
                    title=db_task.title,
                    completed=db_task.completed
                )
            return None
        except Exception as e:
            print(f"Error getting task from database: {e}")
            return None
        finally:
            session.close()

    def update_task(self, task_id: int, new_title: str) -> bool:
        """Update a task in the database."""
        if not new_title or not new_title.strip():
            return False

        session = self._get_session()
        try:
            # Convert the task_id back to the original UUID
            db_task_uuid = self._convert_int_to_uuid(task_id)

            if db_task_uuid is None:
                print(f"Debug: Could not find task with integer ID {task_id}")
                print(f"Debug: Row count: 0")
                return False

            # Update the actual database record using the UUID and user_id
            statement = select(DBTask).where(
                DBTask.id == db_task_uuid,
                DBTask.user_id == self.default_user_id
            )
            db_task = session.exec(statement).first()

            if not db_task:
                print(f"Debug: Could not find task with ID {db_task_uuid} for user {self.default_user_id}")
                print(f"Debug: Row count: 0")
                return False

            db_task.title = new_title.strip()
            db_task.updated_at = datetime.utcnow()
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            print(f"Debug: Updated task, row count: 1")
            return True
        except Exception as e:
            print(f"Error updating task in database: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as complete in the database."""
        session = self._get_session()
        try:
            # Convert the task_id back to the original UUID
            db_task_uuid = self._convert_int_to_uuid(task_id)

            if db_task_uuid is None:
                print(f"Debug: Could not find task with integer ID {task_id}")
                print(f"Debug: Row count: 0")
                return False

            # Update the actual database record using the UUID and user_id
            statement = select(DBTask).where(
                DBTask.id == db_task_uuid,
                DBTask.user_id == self.default_user_id
            )
            db_task = session.exec(statement).first()

            if not db_task:
                print(f"Debug: Could not find task with ID {db_task_uuid} for user {self.default_user_id}")
                print(f"Debug: Row count: 0")
                return False

            db_task.completed = True
            db_task.updated_at = datetime.utcnow()
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            print(f"Debug: Completed task, row count: 1")
            return True
        except Exception as e:
            print(f"Error completing task in database: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def incomplete_task(self, task_id: int) -> bool:
        """Mark a task as incomplete in the database."""
        session = self._get_session()
        try:
            # Convert the task_id back to the original UUID
            db_task_uuid = self._convert_int_to_uuid(task_id)

            if db_task_uuid is None:
                print(f"Debug: Could not find task with integer ID {task_id}")
                print(f"Debug: Row count: 0")
                return False

            # Update the actual database record using the UUID and user_id
            statement = select(DBTask).where(
                DBTask.id == db_task_uuid,
                DBTask.user_id == self.default_user_id
            )
            db_task = session.exec(statement).first()

            if not db_task:
                print(f"Debug: Could not find task with ID {db_task_uuid} for user {self.default_user_id}")
                print(f"Debug: Row count: 0")
                return False

            db_task.completed = False
            db_task.updated_at = datetime.utcnow()
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            print(f"Debug: Marked task as incomplete, row count: 1")
            return True
        except Exception as e:
            print(f"Error marking task as incomplete in database: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def delete_task(self, task_id: int) -> bool:
        """Delete a task from the database."""
        session = self._get_session()
        try:
            # Convert the task_id back to the original UUID
            db_task_uuid = self._convert_int_to_uuid(task_id)

            if db_task_uuid is None:
                print(f"Debug: Could not find task with integer ID {task_id}")
                print(f"Debug: Row count: 0")
                return False

            # Delete the actual database record using the UUID and user_id
            statement = select(DBTask).where(
                DBTask.id == db_task_uuid,
                DBTask.user_id == self.default_user_id
            )
            db_task = session.exec(statement).first()

            if not db_task:
                print(f"Debug: Could not find task with ID {db_task_uuid} for user {self.default_user_id}")
                print(f"Debug: Row count: 0")
                return False

            session.delete(db_task)
            session.commit()
            print(f"Debug: Deleted task, row count: 1")
            return True
        except Exception as e:
            print(f"Error deleting task from database: {e}")
            session.rollback()
            return False
        finally:
            session.close()


class TaskOperationsHandler:
    """
    Handles direct task operations for the backend API without using LLMs.
    """

    def __init__(self):
        self.task_manager = DatabaseTaskManager()

    def process_task_command(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Process task-related commands directly without using LLMs.

        Args:
            user_message: The user's message

        Returns:
            Dictionary with response if it's a task command, None otherwise
        """
        user_message_lower = user_message.lower().strip()

        # Define patterns for different task operations
        patterns = {
            "add_task": [
                r"add.*?task.*?\"([^\"]+)\"",
                r"add.*?task.*?\'([^\']+)\'",
                r"add.*?\btask\b(?:\s+(?:to|for))?\s+(.+?)(?:\.|!|\?|$)",  # Improved: handles "add task to" or "add task"
                r"create.*?task.*?\"([^\"]+)\"",
                r"create.*?task.*?\'([^\']+)\'",
                r"create.*?\btask\b(?:\s+(?:to|for))?\s+(.+?)(?:\.|!|\?|$)",  # Improved: handles "create task to" or "create task"
                r"make.*?task.*?\"([^\"]+)\"",
                r"make.*?task.*?\'([^\']+)\'",
                r"make.*?\btask\b(?:\s+(?:to|for))?\s+(.+?)(?:\.|!|\?|$)"  # Improved: handles "make task to" or "make task"
            ],
            "list_tasks": [
                r"list.*?task",
                r"show(?!.*summary)(?!.*statistic).*?task",  # Show task but not if it contains summary/statistic
                r"display.*?task",
                r"view.*?task",
                r"all.*?task",
                r"what.*?task",
                r"my.*?task",
                r"tasks.*?list",
                r"list.*?all.*?task"
            ],
            "update_task": [
                r"update.*?task.*?(\d+).*?to.*?\"([^\"]+)\"",
                r"update.*?task.*?(\d+).*?to.*?\'([^\']+)\'",
                r"update.*?task.*?(\d+).*?to.*?([^.!?\n]+)$",
                r"change.*?task.*?(\d+).*?to.*?\"([^\"]+)\"",
                r"change.*?task.*?(\d+).*?to.*?\'([^\']+)\'",
                r"change.*?task.*?(\d+).*?to.*?([^.!?\n]+)$",
                r"modify.*?task.*?(\d+).*?to.*?\"([^\"]+)\"",
                r"modify.*?task.*?(\d+).*?to.*?\'([^\']+)\'",
                r"modify.*?task.*?(\d+).*?to.*?([^.!?\n]+)$"
            ],
            "complete_task": [
                r"complete.*?task.*?(\d+)",
                r"finish.*?task.*?(\d+)",
                r"done.*?task.*?(\d+)",
                r"mark.*?task.*?(\d+).*?as.*?complete",
                r"mark.*?task.*?(\d+).*?done"
            ],
            "incomplete_task": [
                r"mark.*?task.*?(\d+).*?as.*?incomplete",
                r"mark.*?task.*?(\d+).*?as.*?not.*?done",
                r"incomplete.*?task.*?(\d+)",
                r"not.*?done.*?task.*?(\d+)"
            ],
            "delete_task": [
                r"delete.*?task.*?(\d+)",
                r"remove.*?task.*?(\d+)",
                r"cancel.*?task.*?(\d+)"
            ],
            "complete_all": [
                r"complete.*?all.*?task",
                r"finish.*?all.*?task",
                r"mark.*?all.*?task.*?as.*?complete",
                r"done.*?with.*?all.*?task"
            ],
            "delete_all": [
                r"delete.*?all.*?task",
                r"remove.*?all.*?task",
                r"clear.*?all.*?task",
                r"get.*?rid.*?of.*?all.*?task"
            ],
            "get_summary": [
                r"summary.*?task",
                r"show.*?task.*?summary",
                r"task.*?summary",
                r"how.*?many.*?task",
                r"statistics.*?task",
                r"count.*?task"
            ]
        }

        # Check for each intent
        for intent, intent_patterns in patterns.items():
            for pattern in intent_patterns:
                match = re.search(pattern, user_message_lower, re.IGNORECASE)
                if match:
                    groups = match.groups()

                    if intent == "add_task":
                        # Handle the new pattern which may have multiple groups
                        title = ""
                        if groups:
                            # Take the last non-empty group which should be the captured title
                            for group in reversed(groups):
                                if group and group.strip():
                                    title = group.strip()
                                    break
                        if title:
                            return self._handle_add_task(title)
                    elif intent == "list_tasks":
                        return self._handle_list_tasks()
                    elif intent == "update_task":
                        if len(groups) >= 2:
                            try:
                                task_id = int(groups[0])
                                # Handle different group patterns - unquoted may have more text
                                new_title = groups[1].strip()
                                # Clean up the new title by removing trailing punctuation
                                new_title = new_title.rstrip('.!?').strip()
                                return self._handle_update_task(task_id, new_title)
                            except ValueError:
                                continue  # Skip if task_id is not a number
                    elif intent in ["complete_task", "incomplete_task", "delete_task"]:
                        if groups:
                            try:
                                task_id = int(groups[0])
                                if intent == "complete_task":
                                    return self._handle_complete_task(task_id)
                                elif intent == "incomplete_task":
                                    return self._handle_incomplete_task(task_id)
                                elif intent == "delete_task":
                                    return self._handle_delete_task(task_id)
                            except ValueError:
                                continue
                    elif intent == "complete_all":
                        return self._handle_complete_all()
                    elif intent == "delete_all":
                        return self._handle_delete_all()
                    elif intent == "get_summary":
                        return self._handle_get_summary()

        # If no pattern matched, return None to indicate it's not a task command
        return None

    def _handle_add_task(self, title: str) -> Dict[str, Any]:
        """Handle add task operation."""
        try:
            result = self.task_manager.add_task(title)
            if result:
                return {
                    "status": "success",
                    "message": f"Added task: {result.title}",
                    "data": {
                        "task_id": result.id,
                        "title": result.title,
                        "completed": result.completed
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to add task",
                    "data": None
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error adding task: {str(e)}",
                "data": None
            }

    def _handle_list_tasks(self) -> Dict[str, Any]:
        """Handle list tasks operation."""
        try:
            tasks = self.task_manager.get_all_tasks()
            if not tasks:
                return {
                    "status": "success",
                    "message": "No tasks found",
                    "data": {"tasks": []}
                }

            task_data = []
            for task in tasks:
                task_data.append({
                    "id": task.id,
                    "title": task.title,
                    "completed": task.completed
                })

            return {
                "status": "success",
                "message": f"Found {len(task_data)} tasks",
                "data": {"tasks": task_data}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error listing tasks: {str(e)}",
                "data": None
            }

    def _handle_update_task(self, task_id: int, new_title: str) -> Dict[str, Any]:
        """Handle update task operation."""
        try:
            result = self.task_manager.update_task(task_id, new_title)
            if result:
                return {
                    "status": "success",
                    "message": f"Updated task {task_id}",
                    "data": {"task_id": task_id, "new_title": new_title}
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to update task {task_id}",
                    "data": None
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error updating task {task_id}: {str(e)}",
                "data": None
            }

    def _handle_complete_task(self, task_id: int) -> Dict[str, Any]:
        """Handle complete task operation."""
        try:
            result = self.task_manager.complete_task(task_id)
            if result:
                task = self.task_manager.get_task_by_id(task_id)
                return {
                    "status": "success",
                    "message": f"Completed task {task_id}: {task.title if task else 'Unknown'}",
                    "data": {"task_id": task_id, "completed": True}
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to complete task {task_id}",
                    "data": None
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error completing task {task_id}: {str(e)}",
                "data": None
            }

    def _handle_incomplete_task(self, task_id: int) -> Dict[str, Any]:
        """Handle incomplete task operation."""
        try:
            result = self.task_manager.incomplete_task(task_id)
            if result:
                task = self.task_manager.get_task_by_id(task_id)
                return {
                    "status": "success",
                    "message": f"Marked task {task_id} as incomplete: {task.title if task else 'Unknown'}",
                    "data": {"task_id": task_id, "completed": False}
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to mark task {task_id} as incomplete",
                    "data": None
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error marking task {task_id} as incomplete: {str(e)}",
                "data": None
            }

    def _handle_delete_task(self, task_id: int) -> Dict[str, Any]:
        """Handle delete task operation."""
        try:
            result = self.task_manager.delete_task(task_id)
            if result:
                return {
                    "status": "success",
                    "message": f"Deleted task {task_id}",
                    "data": {"task_id": task_id}
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to delete task {task_id}",
                    "data": None
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting task {task_id}: {str(e)}",
                "data": None
            }

    def _handle_complete_all(self) -> Dict[str, Any]:
        """Handle complete all tasks operation."""
        try:
            tasks = self.task_manager.get_all_tasks()
            completed_count = 0
            failed_count = 0

            for task in tasks:
                if not task.completed:
                    result = self.task_manager.complete_task(task.id)
                    if result:
                        completed_count += 1
                    else:
                        failed_count += 1

            return {
                "status": "success",
                "message": f"Completed {completed_count} tasks, {failed_count} failed",
                "data": {"completed_count": completed_count, "failed_count": failed_count}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error completing all tasks: {str(e)}",
                "data": None
            }

    def _handle_delete_all(self) -> Dict[str, Any]:
        """Handle delete all tasks operation."""
        try:
            tasks = self.task_manager.get_all_tasks()
            deleted_count = 0
            failed_count = 0

            for task in tasks:
                result = self.task_manager.delete_task(task.id)
                if result:
                    deleted_count += 1
                else:
                    failed_count += 1

            return {
                "status": "success",
                "message": f"Deleted {deleted_count} tasks, {failed_count} failed",
                "data": {"deleted_count": deleted_count, "failed_count": failed_count}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting all tasks: {str(e)}",
                "data": None
            }

    def _handle_get_summary(self) -> Dict[str, Any]:
        """Handle get summary operation."""
        try:
            tasks = self.task_manager.get_all_tasks()
            total_count = len(tasks)
            completed_count = sum(1 for task in tasks if task.completed)
            incomplete_count = total_count - completed_count

            return {
                "status": "success",
                "message": f"Task summary: {total_count} total, {completed_count} completed, {incomplete_count} incomplete",
                "data": {
                    "total_count": total_count,
                    "completed_count": completed_count,
                    "incomplete_count": incomplete_count
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting task summary: {str(e)}",
                "data": None
            }