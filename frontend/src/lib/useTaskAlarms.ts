// src/lib/useTaskAlarms.ts
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlarmStage, DatedTask, alarmStage, dueMoment, formatDue } from './taskTime';

export interface TaskAlert {
  key: string;
  taskId: string;
  stage: AlarmStage;
  message: string;
}

const CHECK_INTERVAL_MS = 30 * 1000;
const FIRED_KEY = 'todo.firedAlarms';

function stageText(task: DatedTask, stage: AlarmStage, now: Date): string {
  if (stage === 'day') return 'is due within a day';
  if (stage === 'hour') return 'is due within the hour';
  if (dueMoment(task)!.getTime() < now.getTime()) return 'is overdue';
  return task.due_time ? 'is due now' : 'is due today';
}

// Remember fired reminders per browser so a reload doesn't repeat them.
// Storage can be unavailable (private mode); alarms still work for the session.
function loadFired(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(FIRED_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

function saveFired(fired: Set<string>) {
  try {
    localStorage.setItem(FIRED_KEY, JSON.stringify(Array.from(fired).slice(-500)));
  } catch {
    /* ignore */
  }
}

function playChime() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    const ctx = new AudioCtx();
    [0, 0.25, 0.5].forEach((offset) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime + offset + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + offset + 0.2);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime + offset);
      osc.stop(ctx.currentTime + offset + 0.22);
    });
    setTimeout(() => ctx.close(), 1000);
  } catch {
    /* audio blocked until the user interacts with the page */
  }
}

export function useTaskAlarms(tasks: DatedTask[]) {
  const [now, setNow] = useState(() => new Date());
  const [alerts, setAlerts] = useState<TaskAlert[]>([]);
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>('default');
  const fired = useRef<Set<string> | null>(null);

  useEffect(() => {
    setPermission(typeof Notification === 'undefined' ? 'unsupported' : Notification.permission);
    const id = setInterval(() => setNow(new Date()), CHECK_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!fired.current) fired.current = loadFired();
    const newAlerts: TaskAlert[] = [];

    for (const task of tasks) {
      const stage = alarmStage(task, now);
      if (!stage) continue;
      // Keyed on the due value too, so rescheduling a task re-arms its alarms
      const key = `${task.id}|${task.due_date}|${task.due_time ?? ''}|${stage}`;
      if (fired.current.has(key)) continue;
      fired.current.add(key);
      newAlerts.push({
        key,
        taskId: task.id,
        stage,
        message: `"${task.title}" ${stageText(task, stage, now)} (${formatDue(task)})`,
      });
    }

    if (newAlerts.length === 0) return;
    saveFired(fired.current);
    setAlerts((prev) => [...prev.filter((a) => !newAlerts.some((n) => n.taskId === a.taskId)), ...newAlerts]);
    playChime();
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      newAlerts.forEach((a) => new Notification('Task reminder', { body: a.message, tag: a.key }));
    }
  }, [tasks, now]);

  const dismiss = useCallback((key: string) => {
    setAlerts((prev) => prev.filter((a) => a.key !== key));
  }, []);

  const enableNotifications = useCallback(async () => {
    if (typeof Notification === 'undefined') return;
    setPermission(await Notification.requestPermission());
  }, []);

  return { now, alerts, dismiss, permission, enableNotifications };
}
