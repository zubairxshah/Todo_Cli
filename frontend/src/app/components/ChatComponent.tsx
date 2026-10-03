// src/app/components/ChatComponent.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { chatApi, ChatHistoryItem } from '../../lib/chatApi';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatComponentProps {
  // Called after every reply; the backend assistant may have changed tasks
  onTasksChanged: () => void;
}

// Examples fill the input instead of sending, so nothing runs by accident
const SUGGESTIONS = [
  'Add "dentist appointment" on coming Tuesday at 3pm',
  'Move the dentist task to Friday',
  'Mark the groceries task as done',
  'Delete the dentist task',
  'What is due this week?',
];

export default function ChatComponent({ onTasksChanged }: ChatComponentProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const addMessage = (text: string, sender: Message['sender']) => {
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, text, sender, timestamp: new Date() },
    ]);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;

    const history: ChatHistoryItem[] = messages.map((m) => ({ role: m.sender, content: m.text }));
    addMessage(text, 'user');
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(text, history);
      addMessage(response.message || 'Done.', 'assistant');
      onTasksChanged();
    } catch (error) {
      console.error('Chat error:', error);
      addMessage('Sorry, I ran into a problem. Please try again.', 'assistant');
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="space-y-3 py-4">
            <p className="text-sm text-slate-500">
              Ask me to add, change, complete or delete tasks in plain words. I know today's date, so
              "next Friday" or "in 10 days" works.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus();
                  }}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700 hover:border-indigo-300 hover:bg-indigo-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <div key={m.id} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                  m.sender === 'user'
                    ? 'rounded-br-sm bg-indigo-600 text-white'
                    : 'rounded-bl-sm bg-slate-100 text-slate-800'
                }`}
              >
                <div className="whitespace-pre-wrap">{m.text}</div>
                <div className={`mt-1 text-[10px] ${m.sender === 'user' ? 'text-indigo-200' : 'text-slate-400'}`}>
                  {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-slate-100 px-4 py-2 text-sm text-slate-500">
              Thinking…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSend} className="border-t border-slate-200 p-3">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. add call mom tomorrow at 6pm"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
