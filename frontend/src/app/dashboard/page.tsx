// src/app/dashboard/page.tsx
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import ChatComponent from '../components/ChatComponent';
import { DueTone, compareByDue, countdown, daysUntil, dueMoment, formatDue } from '../../lib/taskTime';
import { useTaskAlarms } from '../../lib/useTaskAlarms';

interface Task {
  id: string;
  title: string;
  description: string | null;
  completed: boolean;
  due_date: string | null;
  due_time: string | null;
  created_at: string;
  updated_at: string;
  user_id: string;
}

interface TaskDraft {
  title: string;
  description: string;
  due_date: string;
  due_time: string;
}

type Filter = 'all' | 'open' | 'soon' | 'overdue' | 'done';

const EMPTY_DRAFT: TaskDraft = { title: '', description: '', due_date: '', due_time: '' };

const TONE_CLASSES: Record<DueTone, string> = {
  done: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  overdue: 'bg-red-50 text-red-700 ring-red-200',
  urgent: 'bg-orange-50 text-orange-700 ring-orange-200',
  soon: 'bg-amber-50 text-amber-700 ring-amber-200',
  normal: 'bg-slate-50 text-slate-600 ring-slate-200',
};

function toInputDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function addDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return toInputDate(d);
}

// Empty inputs mean "no date/time"; the API expects null for those
function draftToPayload(draft: TaskDraft) {
  return {
    title: draft.title.trim(),
    description: draft.description.trim() || null,
    due_date: draft.due_date || null,
    due_time: draft.due_date && draft.due_time ? draft.due_time : null,
  };
}

function DateFields({ draft, onChange }: { draft: TaskDraft; onChange: (d: TaskDraft) => void }) {
  const quick = [
    { label: 'Today', value: addDays(0) },
    { label: 'Tomorrow', value: addDays(1) },
    { label: 'Next week', value: addDays(7) },
  ];
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-medium text-slate-600">Due date</span>
          <input
            type="date"
            value={draft.due_date}
            onChange={(e) => onChange({ ...draft, due_date: e.target.value })}
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-600">Time (optional)</span>
          <input
            type="time"
            value={draft.due_time}
            disabled={!draft.due_date}
            onChange={(e) => onChange({ ...draft, due_time: e.target.value })}
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:bg-slate-100"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        {quick.map((q) => (
          <button
            key={q.label}
            type="button"
            onClick={() => onChange({ ...draft, due_date: q.value })}
            className={`rounded-full px-3 py-1 text-xs ring-1 ${
              draft.due_date === q.value
                ? 'bg-indigo-600 text-white ring-indigo-600'
                : 'bg-white text-slate-600 ring-slate-200 hover:ring-indigo-300'
            }`}
          >
            {q.label}
          </button>
        ))}
        {draft.due_date && (
          <button
            type="button"
            onClick={() => onChange({ ...draft, due_date: '', due_time: '' })}
            className="rounded-full px-3 py-1 text-xs text-slate-500 hover:text-slate-800"
          >
            Clear date
          </button>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [draft, setDraft] = useState<TaskDraft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<TaskDraft>(EMPTY_DRAFT);
  const [filter, setFilter] = useState<Filter>('open');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();
  const { now, alerts, dismiss, permission, enableNotifications } = useTaskAlarms(tasks);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.get('/api/tasks');
      if (Array.isArray(data)) setTasks(data);
    } catch (err) {
      setError('Could not load your tasks. Is the backend running?');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.push('/login');
      return;
    }
    fetchTasks();
  }, [router, fetchTasks]);

  // API order (creation order) is the numbering the chatbot uses
  const numberOf = useMemo(() => new Map(tasks.map((t, i) => [t.id, i + 1])), [tasks]);

  const stats = useMemo(() => {
    const open = tasks.filter((t) => !t.completed);
    const isOverdue = (t: Task) => (dueMoment(t)?.getTime() ?? Infinity) < now.getTime();
    return {
      open: open.length,
      soon: open.filter((t) => t.due_date && !isOverdue(t) && daysUntil(t.due_date, now) <= 3).length,
      overdue: open.filter(isOverdue).length,
      done: tasks.length - open.length,
    };
  }, [tasks, now]);

  const visibleTasks = useMemo(() => {
    const tone = (t: Task) => countdown(t, now)?.tone;
    const matches: Record<Filter, (t: Task) => boolean> = {
      all: () => true,
      open: (t) => !t.completed,
      soon: (t) => ['urgent', 'soon'].includes(tone(t) ?? ''),
      overdue: (t) => tone(t) === 'overdue',
      done: (t) => t.completed,
    };
    return tasks.filter(matches[filter]).sort(compareByDue);
  }, [tasks, filter, now]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.title.trim()) return;
    try {
      const created = await api.post('/api/tasks', draftToPayload(draft));
      if (created) {
        setTasks((prev) => [...prev, created]);
        setDraft(EMPTY_DRAFT);
        setError('');
      }
    } catch (err) {
      setError('Could not add the task. Please try again.');
      console.error(err);
    }
  };

  const handleToggle = async (id: string) => {
    try {
      const updated = await api.patch(`/api/tasks/${id}/toggle`, {});
      if (updated) setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
    } catch (err) {
      setError('Could not update the task.');
      console.error(err);
    }
  };

  const handleDelete = async (task: Task) => {
    if (!window.confirm(`Delete "${task.title}"?`)) return;
    try {
      await api.delete(`/api/tasks/${task.id}`);
      setTasks((prev) => prev.filter((t) => t.id !== task.id));
    } catch (err) {
      setError('Could not delete the task.');
      console.error(err);
    }
  };

  const startEdit = (task: Task) => {
    setEditingId(task.id);
    setEditDraft({
      title: task.title,
      description: task.description || '',
      due_date: task.due_date || '',
      due_time: task.due_time || '',
    });
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingId || !editDraft.title.trim()) return;
    try {
      const updated = await api.put(`/api/tasks/${editingId}`, draftToPayload(editDraft));
      if (updated) {
        setTasks((prev) => prev.map((t) => (t.id === editingId ? updated : t)));
        setEditingId(null);
      }
    } catch (err) {
      setError('Could not save the task.');
      console.error(err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">Loading…</div>;
  }

  const filters: { key: Filter; label: string; count?: number }[] = [
    { key: 'open', label: 'Open', count: stats.open },
    { key: 'soon', label: 'Due soon', count: stats.soon },
    { key: 'overdue', label: 'Overdue', count: stats.overdue },
    { key: 'done', label: 'Done', count: stats.done },
    { key: 'all', label: 'All', count: tasks.length },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">My Tasks</h1>
            <p className="text-sm text-slate-500">
              {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {permission === 'granted' ? (
              <span className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700">
                🔔 Alarms on
              </span>
            ) : permission !== 'unsupported' ? (
              <button
                onClick={enableNotifications}
                title={permission === 'denied' ? 'Notifications are blocked in your browser settings' : ''}
                className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                🔔 Enable alarm notifications
              </button>
            ) : null}
            <button
              onClick={handleLogout}
              className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {alerts.length > 0 && (
          <div className="space-y-2" role="alert">
            {alerts.map((a) => (
              <div
                key={a.key}
                className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm ${
                  a.stage === 'due' ? 'border-red-200 bg-red-50 text-red-800' : 'border-amber-200 bg-amber-50 text-amber-800'
                }`}
              >
                <span>⏰ {a.message}</span>
                <button onClick={() => dismiss(a.key)} className="ml-4 text-xs font-medium underline">
                  Dismiss
                </button>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <span>{error}</span>
            <button onClick={() => setError('')} className="ml-4 text-xs font-medium underline">
              Dismiss
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'Open', value: stats.open, cls: 'text-slate-900' },
            { label: 'Due in 3 days', value: stats.soon, cls: 'text-amber-600' },
            { label: 'Overdue', value: stats.overdue, cls: 'text-red-600' },
            { label: 'Completed', value: stats.done, cls: 'text-emerald-600' },
          ].map((s) => (
            <div key={s.label} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{s.label}</div>
              <div className={`mt-1 text-2xl font-semibold ${s.cls}`}>{s.value}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <form onSubmit={handleAdd} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
              <h2 className="text-base font-semibold text-slate-900">Add a task</h2>
              <input
                type="text"
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                placeholder="What needs to be done?"
                required
                className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <textarea
                value={draft.description}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                placeholder="Notes (optional)"
                rows={2}
                className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <DateFields draft={draft} onChange={setDraft} />
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Add task
              </button>
            </form>

            <section className="rounded-xl border border-slate-200 bg-white">
              <div className="flex flex-wrap gap-1 border-b border-slate-200 p-2">
                {filters.map((f) => (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    className={`rounded-lg px-3 py-1.5 text-sm ${
                      filter === f.key ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {f.label}
                    <span className={`ml-1.5 text-xs ${filter === f.key ? 'text-slate-300' : 'text-slate-400'}`}>
                      {f.count}
                    </span>
                  </button>
                ))}
              </div>

              {visibleTasks.length === 0 ? (
                <p className="px-5 py-10 text-center text-sm text-slate-500">
                  {tasks.length === 0 ? 'No tasks yet. Add one above or ask the assistant.' : 'Nothing here.'}
                </p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {visibleTasks.map((task) => {
                    const cd = countdown(task, now);
                    if (editingId === task.id) {
                      return (
                        <li key={task.id} className="bg-indigo-50/40 p-4">
                          <form onSubmit={handleSaveEdit} className="space-y-3">
                            <input
                              type="text"
                              value={editDraft.title}
                              onChange={(e) => setEditDraft({ ...editDraft, title: e.target.value })}
                              required
                              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            />
                            <textarea
                              value={editDraft.description}
                              onChange={(e) => setEditDraft({ ...editDraft, description: e.target.value })}
                              rows={2}
                              placeholder="Notes"
                              className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            />
                            <DateFields draft={editDraft} onChange={setEditDraft} />
                            <div className="flex gap-2">
                              <button type="submit" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm text-white">
                                Save
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingId(null)}
                                className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
                              >
                                Cancel
                              </button>
                            </div>
                          </form>
                        </li>
                      );
                    }
                    return (
                      <li key={task.id} className="group flex items-start gap-3 px-4 py-3 hover:bg-slate-50">
                        <input
                          type="checkbox"
                          checked={task.completed}
                          onChange={() => handleToggle(task.id)}
                          aria-label={`Mark "${task.title}" ${task.completed ? 'open' : 'done'}`}
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs text-slate-400">#{numberOf.get(task.id)}</span>
                            <span
                              className={`text-sm font-medium ${task.completed ? 'text-slate-400 line-through' : 'text-slate-900'}`}
                            >
                              {task.title}
                            </span>
                            {cd && (
                              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${TONE_CLASSES[cd.tone]}`}>
                                {cd.label}
                              </span>
                            )}
                          </div>
                          {task.due_date && <div className="mt-0.5 text-xs text-slate-500">📅 {formatDue(task)}</div>}
                          {task.description && <p className="mt-1 text-sm text-slate-600">{task.description}</p>}
                        </div>
                        <div className="flex shrink-0 gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100">
                          <button
                            onClick={() => startEdit(task)}
                            className="rounded-md px-2 py-1 text-xs text-slate-600 hover:bg-slate-200"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(task)}
                            className="rounded-md px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                          >
                            Delete
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </div>

          <aside className="lg:sticky lg:top-6 lg:self-start">
            <div className="flex h-[36rem] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-200 px-4 py-3">
                <h2 className="text-base font-semibold text-slate-900">AI Assistant</h2>
                <p className="text-xs text-slate-500">Manages your tasks for you</p>
              </div>
              <div className="min-h-0 flex-1">
                <ChatComponent onTasksChanged={fetchTasks} />
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
