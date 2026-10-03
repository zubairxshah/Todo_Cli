"""
Task execution service that bridges natural language commands to actual task operations
"""

import json
import re
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
import uuid
from datetime import datetime, timezone

try:
    # Try relative imports first
    from ..models.task import Task, TaskCreate, TaskUpdate
except ImportError:
    # Fall back to absolute imports
    from models.task import Task, TaskCreate, TaskUpdate


class TaskExecutionService:
    """Service to execute task operations based on natural language parsing"""
    
    @staticmethod
    def parse_task_command(message: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language command to extract task operation
        Returns: Dict with 'action', 'title', 'description', 'task_id', 'completed' etc.
        """
        message_lower = message.lower()
        
        # Add/Create task
        if any(phrase in message_lower for phrase in ['add task', 'create task', 'new task', 'add a task']):
            # Extract task title - usually after "add task" or similar
            match = re.search(r'(?:add|create|new)\s+(?:a\s+)?task\s+(.+?)(?:\.|$)', message, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                description_match = re.search(r'(?:description|details?)[\s:]+(.+?)(?:\.|$)', message, re.IGNORECASE)
                description = description_match.group(1).strip() if description_match else None
                
                return {
                    'action': 'create',
                    'title': title,
                    'description': description
                }
        
        # Update task
        if any(phrase in message_lower for phrase in ['update task', 'edit task', 'change task', 'modify task']):
            task_id_match = re.search(r'task\s+(\d+)', message, re.IGNORECASE)
            title_match = re.search(r'(?:title|name)\s+(?:to\s+)?["\']?([^"\'\.]+)["\']?', message, re.IGNORECASE)
            description_match = re.search(r'(?:description|details?)\s+(?:to\s+)?["\']?([^"\'\.]+)["\']?', message, re.IGNORECASE)
            completed_match = re.search(r'(?:mark|set)\s+(?:it\s+|this\s+)?(?:as\s+)?(?:completed?|done|finished)', message, re.IGNORECASE)
            
            if task_id_match:
                return {
                    'action': 'update',
                    'task_id': int(task_id_match.group(1)),
                    'title': title_match.group(1) if title_match else None,
                    'description': description_match.group(1) if description_match else None,
                    'completed': True if completed_match else None
                }
        
        # Complete/Mark as done
        if any(phrase in message_lower for phrase in ['mark as complete', 'mark as done', 'complete task', 'finish task', 'mark complete']):
            task_id_match = re.search(r'task\s+(\d+)', message, re.IGNORECASE)
            if task_id_match:
                return {
                    'action': 'toggle',
                    'task_id': int(task_id_match.group(1))
                }
        
        # Delete task
        if any(phrase in message_lower for phrase in ['delete task', 'remove task', 'remove the task', 'delete the task']):
            task_id_match = re.search(r'task\s+(\d+)', message, re.IGNORECASE)
            if task_id_match:
                return {
                    'action': 'delete',
                    'task_id': int(task_id_match.group(1))
                }
        
        # List tasks
        if any(phrase in message_lower for phrase in ['list tasks', 'show tasks', 'get tasks', 'what tasks', 'all tasks']):
            return {'action': 'list'}
        
        return None
    
    @staticmethod
    def execute_create_task(
        title: str,
        description: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Create a new task"""
        if not session or not user_id:
            return {
                'success': False,
                'message': f'Created task "{title}" (simulated - no database session)',
                'task': None
            }
        
        try:
            db_task = Task(
                title=title,
                description=description,
                completed=False,
                user_id=user_id
            )
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            
            return {
                'success': True,
                'message': f'Successfully created task: "{title}"',
                'task': db_task
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to create task: {str(e)}',
                'task': None
            }
    
    @staticmethod
    def _get_user_task(session: Session, user_id: uuid.UUID, task_id) -> Optional[Task]:
        """Resolve a task by its 1-based position in the user's list, or by UUID"""
        if isinstance(task_id, int):
            tasks = session.exec(
                select(Task).where(Task.user_id == user_id).order_by(Task.created_at)
            ).all()
            return tasks[task_id - 1] if 1 <= task_id <= len(tasks) else None
        return session.get(Task, uuid.UUID(str(task_id)))

    @staticmethod
    def execute_list_tasks(
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """List all tasks for a user"""
        if not session or not user_id:
            return {
                'success': False,
                'message': 'Unable to fetch tasks (no database session)',
                'tasks': []
            }
        
        try:
            tasks = session.exec(
                select(Task).where(Task.user_id == user_id).order_by(Task.created_at)
            ).all()
            task_list = [
                {
                    'id': str(t.id),
                    'title': t.title,
                    'completed': t.completed,
                    'description': t.description
                }
                for t in tasks
            ]
            
            if not tasks:
                return {
                    'success': True,
                    'message': 'No tasks found',
                    'tasks': []
                }
            
            task_summary = '\n'.join([
                f"- Task {i+1}: {t['title']} {'✓' if t['completed'] else '○'}"
                for i, t in enumerate(task_list)
            ])
            
            return {
                'success': True,
                'message': f'You have {len(tasks)} task(s):\n{task_summary}',
                'tasks': task_list
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to fetch tasks: {str(e)}',
                'tasks': []
            }
    
    @staticmethod
    def execute_update_task(
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        completed: Optional[bool] = None,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Update a task"""
        if not session or not user_id:
            updates = []
            if title:
                updates.append(f'title to "{title}"')
            if description:
                updates.append(f'description')
            if completed is not None:
                updates.append(f'marked as {"completed" if completed else "incomplete"}')
            
            message = f'Updated task {task_id}: {", ".join(updates)}' if updates else f'Updated task {task_id}'
            return {
                'success': False,
                'message': f'{message} (simulated - no database session)',
                'task': None
            }
        
        try:
            db_task = TaskExecutionService._get_user_task(session, user_id, task_id)
            
            if not db_task:
                return {
                    'success': False,
                    'message': f'Task {task_id} not found',
                    'task': None
                }
            
            if db_task.user_id != user_id:
                return {
                    'success': False,
                    'message': 'Not authorized to update this task',
                    'task': None
                }
            
            updates = []
            if title:
                db_task.title = title
                updates.append(f'title to "{title}"')
            if description is not None:
                db_task.description = description
                updates.append('description')
            if completed is not None:
                db_task.completed = completed
                updates.append(f'{"completed" if completed else "incomplete"}')
            
            if not updates:
                return {
                    'success': True,
                    'message': f'Task {task_id} unchanged',
                    'task': db_task
                }
            
            db_task.updated_at = datetime.now(timezone.utc)
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            
            return {
                'success': True,
                'message': f'Updated task {task_id}: {", ".join(updates)}',
                'task': db_task
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to update task: {str(e)}',
                'task': None
            }
    
    @staticmethod
    def execute_toggle_task(
        task_id: int,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Toggle task completion status"""
        if not session or not user_id:
            return {
                'success': False,
                'message': f'Toggled task {task_id} (simulated - no database session)',
                'task': None
            }
        
        try:
            db_task = TaskExecutionService._get_user_task(session, user_id, task_id)
            
            if not db_task:
                return {
                    'success': False,
                    'message': f'Task {task_id} not found',
                    'task': None
                }
            
            if db_task.user_id != user_id:
                return {
                    'success': False,
                    'message': 'Not authorized to update this task',
                    'task': None
                }
            
            db_task.completed = not db_task.completed
            db_task.updated_at = datetime.now(timezone.utc)
            session.add(db_task)
            session.commit()
            session.refresh(db_task)
            
            status = 'completed' if db_task.completed else 'incomplete'
            return {
                'success': True,
                'message': f'Task {task_id} marked as {status}',
                'task': db_task
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to toggle task: {str(e)}',
                'task': None
            }
    
    @staticmethod
    def execute_delete_task(
        task_id: int,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Delete a task"""
        if not session or not user_id:
            return {
                'success': False,
                'message': f'Deleted task {task_id} (simulated - no database session)',
            }
        
        try:
            db_task = TaskExecutionService._get_user_task(session, user_id, task_id)
            
            if not db_task:
                return {
                    'success': False,
                    'message': f'Task {task_id} not found',
                }
            
            if db_task.user_id != user_id:
                return {
                    'success': False,
                    'message': 'Not authorized to delete this task',
                }
            
            session.delete(db_task)
            session.commit()
            
            return {
                'success': True,
                'message': f'Task {task_id} deleted successfully',
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to delete task: {str(e)}',
            }
