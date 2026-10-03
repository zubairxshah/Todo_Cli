// src/lib/taskTime.ts
// Due dates are stored as a local date ("YYYY-MM-DD") plus optional local time
// ("HH:MM"), so everything here is computed in the browser's own timezone.

export interface DatedTask {
  id: string;
  title: string;
  completed: boolean;
  due_date?: string | null;
  due_time?: string | null;
}

export type DueTone = 'done' | 'overdue' | 'urgent' | 'soon' | 'normal';

// Date-only tasks remind at this local time
const DEFAULT_ALARM_HOUR = 9;
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function parseLocalDate(value: string): Date {
  const [y, m, d] = value.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Calendar days from today to the due date (negative when past). */
export function daysUntil(dueDate: string, now: Date): number {
  return Math.round((parseLocalDate(dueDate).getTime() - startOfDay(now).getTime()) / MS_PER_DAY);
}

/** The moment a task is due: its time, or end of day when it has none. */
export function dueMoment(task: DatedTask): Date | null {
  if (!task.due_date) return null;
  const d = parseLocalDate(task.due_date);
  if (task.due_time) {
    const [h, min] = task.due_time.split(':').map(Number);
    d.setHours(h, min, 0, 0);
  } else {
    d.setHours(23, 59, 59, 999);
  }
  return d;
}

/** When reminders count down to: the due time, or 09:00 on the due date. */
export function alarmMoment(task: DatedTask): Date | null {
  if (!task.due_date) return null;
  if (task.due_time) return dueMoment(task);
  const d = parseLocalDate(task.due_date);
  d.setHours(DEFAULT_ALARM_HOUR, 0, 0, 0);
  return d;
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

function formatDuration(ms: number): string {
  const totalMinutes = Math.max(1, Math.round(ms / 60000));
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function countdown(task: DatedTask, now: Date): { label: string; tone: DueTone } | null {
  if (task.completed) return { label: 'Done', tone: 'done' };
  if (!task.due_date) return null;

  const due = dueMoment(task)!;
  const days = daysUntil(task.due_date, now);

  if (due.getTime() < now.getTime()) {
    return { label: days < 0 ? `Overdue by ${plural(-days, 'day')}` : 'Overdue', tone: 'overdue' };
  }
  if (days === 0) {
    return task.due_time
      ? { label: `Due in ${formatDuration(due.getTime() - now.getTime())}`, tone: 'urgent' }
      : { label: 'Due today', tone: 'urgent' };
  }
  if (days === 1) return { label: 'Due tomorrow', tone: 'soon' };
  return { label: `${plural(days, 'day')} left`, tone: days <= 3 ? 'soon' : 'normal' };
}

export function formatDue(task: DatedTask): string {
  if (!task.due_date) return '';
  const d = parseLocalDate(task.due_date);
  const date = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  return task.due_time ? `${date}, ${task.due_time}` : date;
}

export type AlarmStage = 'day' | 'hour' | 'due';

/** The latest reminder stage the task has reached, or null if none yet. */
export function alarmStage(task: DatedTask, now: Date): AlarmStage | null {
  if (task.completed) return null;
  const at = alarmMoment(task);
  if (!at) return null;
  const msLeft = at.getTime() - now.getTime();
  if (msLeft <= 0) return 'due';
  if (task.due_time && msLeft <= 60 * 60 * 1000) return 'hour';
  if (msLeft <= MS_PER_DAY) return 'day';
  return null;
}

/** Sort open tasks by due moment (undated last), completed tasks at the end. */
export function compareByDue(a: DatedTask, b: DatedTask): number {
  if (a.completed !== b.completed) return a.completed ? 1 : -1;
  const da = dueMoment(a)?.getTime() ?? Infinity;
  const db = dueMoment(b)?.getTime() ?? Infinity;
  return da - db;
}
