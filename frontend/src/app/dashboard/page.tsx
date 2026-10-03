// src/app/dashboard/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import ChatComponent from '../components/ChatComponent';

interface Task {
  id: string;  // UUID as string
  title: string;
  description: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
  user_id: string;  // UUID as string
}

interface EditTaskState {
  id: string | null;
  title: string;
  description: string;
}

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState({ title: '', description: '' });
  const [editTask, setEditTask] = useState<EditTaskState>({ id: null, title: '', description: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  // Check authentication on component mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      setLoading(false); // Stop loading since we're redirecting
      return;
    }

    fetchTasks();
  }, [router]);

  const fetchTasks = async () => {
    try {
      const data = await api.get('/api/tasks');
      if (data) {
        setTasks(Array.isArray(data) ? data : (data.tasks || data));
      }
    } catch (err) {
      setError('An error occurred while fetching tasks');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const createdTask = await api.post('/api/tasks', newTask);
      if (createdTask) {
        setTasks(prevTasks => [...prevTasks, createdTask]);
        setNewTask({ title: '', description: '' });
        setError(''); // Clear any previous errors
      }
    } catch (err) {
      setError('An error occurred while adding task. Please try again.');
      console.error('Add task error:', err);
    }
  };

  const handleToggleTask = async (taskId: string) => {
    console.log('Toggling task with ID:', taskId);
    try {
      const updatedTask = await api.patch(`/api/tasks/${taskId}/toggle`, {});
      if (updatedTask) {
        console.log('Updated task:', updatedTask);
        setTasks(prevTasks => prevTasks.map(task =>
          task.id === taskId ? updatedTask : task
        ));
        setError(''); // Clear any previous errors
      }
    } catch (err) {
      setError('An error occurred while updating task. Please try again.');
      console.error('Toggle task error:', err);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    console.log('Deleting task with ID:', taskId);
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return;
    }

    try {
      const result = await api.delete(`/api/tasks/${taskId}`);
      if (result && result.success !== false) {
        setTasks(prevTasks => prevTasks.filter(task => task.id !== taskId));
        setError(''); // Clear any previous errors
      }
    } catch (err) {
      setError('An error occurred while deleting task. Please try again.');
      console.error('Delete task error:', err);
    }
  };

  const handleEditTask = (task: Task) => {
    setEditTask({
      id: task.id,
      title: task.title,
      description: task.description
    });
  };

  const handleUpdateTask = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editTask.id) return;

    try {
      const updatedTask = await api.put(`/api/tasks/${editTask.id}`, {
        title: editTask.title,
        description: editTask.description
      });

      if (updatedTask) {
        setTasks(prevTasks => prevTasks.map(task =>
          task.id === editTask.id ? updatedTask : task
        ));
        setEditTask({ id: null, title: '', description: '' });
        setError(''); // Clear any previous errors
      }
    } catch (err) {
      setError('An error occurred while updating task. Please try again.');
      console.error('Update task error:', err);
    }
  };

  const handleCancelEdit = () => {
    setEditTask({ id: null, title: '', description: '' });
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">Todo Dashboard</h1>
            </div>
            <div className="flex items-center">
              <button
                onClick={handleLogout}
                className="ml-4 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {error && (
            <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left column - Task management */}
            <div>
              <form onSubmit={handleAddTask} className="mb-8 p-4 bg-white rounded-lg shadow">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Add New Task</h2>
                <div className="grid grid-cols-1 gap-6">
                  <div>
                    <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                      Title
                    </label>
                    <input
                      type="text"
                      id="title"
                      value={newTask.title}
                      onChange={(e) => setNewTask({...newTask, title: e.target.value})}
                      required
                      className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                      Description
                    </label>
                    <textarea
                      id="description"
                      value={newTask.description}
                      onChange={(e) => setNewTask({...newTask, description: e.target.value})}
                      className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      rows={3}
                    />
                  </div>
                  <div>
                    <button
                      type="submit"
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      Add Task
                    </button>
                  </div>
                </div>
              </form>

              <div>
                <h2 className="text-lg font-medium text-gray-900 mb-4">Your Tasks</h2>
                {tasks.length === 0 ? (
                  <p className="text-gray-500">No tasks yet. Add a new task to get started!</p>
                ) : (
                  <ul className="bg-white rounded-lg shadow overflow-hidden">
                    {tasks.map((task) => (
                      editTask.id === task.id ? (
                        // Edit form for the task being edited
                        <li key={task.id} className="border-b border-gray-200 last:border-b-0 p-4 bg-blue-50">
                          <form onSubmit={handleUpdateTask} className="space-y-3">
                            <div>
                              <input
                                type="text"
                                value={editTask.title}
                                onChange={(e) => setEditTask({...editTask, title: e.target.value})}
                                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                                required
                              />
                            </div>
                            <div>
                              <textarea
                                value={editTask.description}
                                onChange={(e) => setEditTask({...editTask, description: e.target.value})}
                                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                                rows={2}
                              />
                            </div>
                            <div className="flex space-x-2">
                              <button
                                type="submit"
                                className="px-3 py-1 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded"
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                onClick={handleCancelEdit}
                                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900"
                              >
                                Cancel
                              </button>
                            </div>
                          </form>
                        </li>
                      ) : (
                        // Normal task display
                        <li key={task.id} className="border-b border-gray-200 last:border-b-0">
                          <div className="p-4 flex items-center justify-between">
                            <div className="flex items-center">
                              <input
                                type="checkbox"
                                checked={task.completed}
                                onChange={() => handleToggleTask(task.id)}
                                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                              />
                              <span className={`ml-3 ${task.completed ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                                {task.title}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="text-sm text-gray-500">
                                {new Date(task.created_at).toLocaleDateString()}
                              </span>
                              <button
                                onClick={() => handleEditTask(task)}
                                className="ml-2 px-3 py-1 text-sm text-blue-600 hover:text-blue-900"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteTask(task.id)}
                                className="ml-2 px-3 py-1 text-sm text-red-600 hover:text-red-900"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                          {task.description && (
                            <div className="ml-7 pl-4 pb-2 text-sm text-gray-600">
                              {task.description}
                            </div>
                          )}
                        </li>
                      )
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Right column - Chat component */}
            <div>
              <div className="bg-white rounded-lg shadow p-4">
                <h2 className="text-lg font-medium text-gray-900 mb-4">AI Assistant</h2>
                <ChatComponent tasks={tasks} setTasks={setTasks} setError={setError} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}