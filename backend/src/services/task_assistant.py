"""
LLM task assistant: gives the model the user's real task list, today's date and
a calendar, plus tools to create/update/delete/complete tasks, and executes the
tool calls against the database.
"""

import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

try:
    from ..models.task import Task, _check_due_time
except ImportError:
    from models.task import Task, _check_due_time

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5
CALENDAR_DAYS = 60
MAX_HISTORY_MESSAGES = 10

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short task title"},
                    "description": {"type": "string"},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD, taken from the calendar"},
                    "due_time": {"type": "string", "description": "HH:MM 24-hour, only if the user gave a time"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Change an existing task. Only pass the fields that should change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_number": {"type": "integer", "description": "Number of the task in the task list"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD, or empty string to clear"},
                    "due_time": {"type": "string", "description": "HH:MM 24-hour, or empty string to clear"},
                    "completed": {"type": "boolean"},
                },
                "required": ["task_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Permanently delete a task.",
            "parameters": {
                "type": "object",
                "properties": {"task_number": {"type": "integer"}},
                "required": ["task_number"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are the assistant inside a todo app. You manage the user's tasks with the tools provided.

Today is {today_long}. The user's local time is {now_time}.

Calendar (use it for every date; never compute weekdays yourself):
{calendar}

The user's tasks (number. title | due | status):
{tasks}

Rules:
- To change, complete or delete a task, call the tool. Never claim you changed something unless the tool returned ok.
- Identify the task from the user's words and the conversation ("it", "that one", "the groceries task") by matching titles. If more than one task could match, or none does, ask which one instead of guessing.
- Relative dates: "tomorrow" is the day after today. A weekday name ("on Tuesday", "this Friday", "coming Monday") means the first such day after today in the calendar; "next week" means 7 days from today; "in N days" counts from today. Read the date from the calendar.
- If the user gives no date for a new task, leave due_date empty. Set due_time only if a time was given.
- Do not create a task that already exists with the same title and date; tell the user instead.
- Reply briefly. When you set a date, say it as weekday plus date, e.g. "Tue, Oct 6"."""


def _parse_client_now(client_now: Optional[str]) -> datetime:
    """The browser sends its local time ("YYYY-MM-DDTHH:MM") so "today" is the
    user's today, not the server's."""
    if client_now:
        try:
            return datetime.fromisoformat(client_now[:16])
        except ValueError:
            logger.warning(f"Ignoring invalid client_now: {client_now!r}")
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_calendar(today: date) -> str:
    lines = []
    for offset in range(CALENDAR_DAYS):
        day = today + timedelta(days=offset)
        label = " (today)" if offset == 0 else " (tomorrow)" if offset == 1 else ""
        lines.append(f"{day:%a %Y-%m-%d}{label}")
    return "\n".join(lines)


def _format_due(task: Task) -> str:
    if not task.due_date:
        return "no due date"
    due = f"{task.due_date:%a %Y-%m-%d}"
    return f"{due} {task.due_time}" if task.due_time else due


def _format_tasks(tasks: List[Task]) -> str:
    if not tasks:
        return "(no tasks yet)"
    return "\n".join(
        f"{i}. {t.title} | {_format_due(t)} | {'done' if t.completed else 'open'}"
        + (f" | note: {t.description}" if t.description else "")
        for i, t in enumerate(tasks, start=1)
    )


def _parse_date(value: Any) -> Tuple[bool, Optional[date]]:
    """Returns (ok, date). Empty string clears the date."""
    if value in (None, ""):
        return True, None
    try:
        return True, date.fromisoformat(str(value))
    except ValueError:
        return False, None


class TaskAssistant:
    def __init__(self, async_client, model: Optional[str] = None):
        self.client = async_client
        self.model = model or os.getenv("OPEN_ROUTER_MODEL", "openai/gpt-4o-mini")

    def _load_tasks(self, session: Session, user_id: uuid.UUID) -> List[Task]:
        return list(session.exec(
            select(Task).where(Task.user_id == user_id).order_by(Task.created_at)
        ).all())

    async def run(
        self,
        message: str,
        session: Session,
        user_id: uuid.UUID,
        history: Optional[List[Dict[str, str]]] = None,
        client_now: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Returns (reply, tasks_changed)."""
        now = _parse_client_now(client_now)
        today = now.date()
        tasks = self._load_tasks(session, user_id)
        # Numbers refer to the list shown to the model; keep them stable for
        # the whole turn even if tasks are created or deleted along the way
        numbered = {i: t.id for i, t in enumerate(tasks, start=1)}

        system = SYSTEM_PROMPT.format(
            today_long=f"{today:%A, %B %d, %Y} ({today.isoformat()})",
            now_time=f"{now:%H:%M}",
            calendar=_build_calendar(today),
            tasks=_format_tasks(tasks),
        )

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]
        for item in (history or [])[-MAX_HISTORY_MESSAGES:]:
            if item.get("role") in ("user", "assistant") and item.get("content"):
                messages.append({"role": item["role"], "content": str(item["content"])[:2000]})
        messages.append({"role": "user", "content": message})

        changed = False
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=500,
            )
            reply = response.choices[0].message
            if not reply.tool_calls:
                return (reply.content or "Done.").strip(), changed

            messages.append({
                "role": "assistant",
                "content": reply.content or "",
                "tool_calls": [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    for c in reply.tool_calls
                ],
            })
            for call in reply.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self.execute_tool(call.function.name, args, session, user_id, numbered)
                logger.info(f"Tool {call.function.name}({args}) -> {result}")
                changed = changed or result.get("ok", False)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

        return "Sorry, I couldn't finish that request. Please try rephrasing it.", changed

    def execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        session: Session,
        user_id: uuid.UUID,
        numbered: Dict[int, uuid.UUID],
    ) -> Dict[str, Any]:
        if name == "create_task":
            return self._create(args, session, user_id, numbered)
        if name in ("update_task", "delete_task"):
            task = self._resolve(args.get("task_number"), session, user_id, numbered)
            if task is None:
                return {"ok": False, "error": f"No task number {args.get('task_number')} in the list"}
            if name == "delete_task":
                session.delete(task)
                session.commit()
                return {"ok": True, "deleted": task.title}
            return self._update(task, args, session)
        return {"ok": False, "error": f"Unknown tool {name}"}

    def _resolve(self, number, session, user_id, numbered) -> Optional[Task]:
        try:
            task_id = numbered.get(int(number))
        except (TypeError, ValueError):
            return None
        task = session.get(Task, task_id) if task_id else None
        return task if task and task.user_id == user_id else None

    def _create(self, args, session, user_id, numbered) -> Dict[str, Any]:
        title = (args.get("title") or "").strip()
        if not title:
            return {"ok": False, "error": "title is required"}
        ok, due_date = _parse_date(args.get("due_date"))
        if not ok:
            return {"ok": False, "error": "due_date must be YYYY-MM-DD"}
        try:
            due_time = _check_due_time(args.get("due_time"))
        except ValueError as e:
            return {"ok": False, "error": str(e)}

        task = Task(
            title=title,
            description=(args.get("description") or None),
            due_date=due_date,
            due_time=due_time,
            user_id=user_id,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        number = max(numbered, default=0) + 1
        numbered[number] = task.id
        return {"ok": True, "task_number": number, "title": task.title, "due": _format_due(task)}

    def _update(self, task: Task, args, session) -> Dict[str, Any]:
        if "title" in args and (args["title"] or "").strip():
            task.title = args["title"].strip()
        if "description" in args:
            task.description = args["description"] or None
        if "due_date" in args:
            ok, due_date = _parse_date(args["due_date"])
            if not ok:
                return {"ok": False, "error": "due_date must be YYYY-MM-DD"}
            task.due_date = due_date
            if due_date is None:
                task.due_time = None
        if "due_time" in args:
            try:
                task.due_time = _check_due_time(args["due_time"])
            except ValueError as e:
                return {"ok": False, "error": str(e)}
        if "completed" in args and args["completed"] is not None:
            task.completed = bool(args["completed"])

        task.updated_at = datetime.now(timezone.utc)
        session.add(task)
        session.commit()
        session.refresh(task)
        return {"ok": True, "title": task.title, "due": _format_due(task),
                "status": "done" if task.completed else "open"}
