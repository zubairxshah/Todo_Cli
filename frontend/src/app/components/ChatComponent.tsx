// src/app/components/ChatComponent.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { chatApi } from '../../lib/chatApi';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface Task {
  id: string;  // UUID as string
  title: string;
  description: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
  user_id: string;  // UUID as string
}

// Define the prop type to accept the tasks and setTasks function
interface ChatComponentProps {
  tasks: Task[];
  setTasks: React.Dispatch<React.SetStateAction<Task[]>>;
  setError?: React.Dispatch<React.SetStateAction<string>>;
}

export default function ChatComponent({ tasks, setTasks, setError }: ChatComponentProps) {
  const [inputMessage, setInputMessage] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Helper function to detect if the response contains task-related intents
  const detectTaskIntent = (responseText: string): {
    isTaskIntent: boolean;
    operation?: 'create' | 'delete' | 'update' | 'complete' | 'list' | 'summary';
    title?: string;
    description?: string;
    taskId?: number | string;
  } => {
    // Look for patterns indicating various task operations
    const lowerText = responseText.toLowerCase();

    // Check for task creation keywords
    const addTaskPattern = /(?:add|create|make|new)\s+(?:a\s+)?(?:task|todo|to-do)\s+(?:to|called|named|about|regarding)?\s*(.+)/i;
    const taskPattern = /(?:task|todo|to-do):\s*(.+)/i;

    let titleMatch = addTaskPattern.exec(responseText);
    if (!titleMatch) {
      titleMatch = taskPattern.exec(responseText);
    }

    if (titleMatch) {
      let title = titleMatch[1].trim();

      // Extract just the title part (before any punctuation or extra details)
      const titleEnd = title.indexOf('.') !== -1 ? title.indexOf('.') : title.length;
      title = title.substring(0, titleEnd).trim();

      // Remove common prefixes like "to ", "for ", etc.
      title = title.replace(/^(?:to|for|about|regarding)\s+/, '');

      if (title) {
        return {
          isTaskIntent: true,
          operation: 'create',
          title: title.charAt(0).toUpperCase() + title.slice(1),
          description: responseText
        };
      }
    }

    // Check for task deletion keywords
    const deletePattern = /(?:deleted|removed|completed|marked as done|buy|bye)\s+.*/i;
    if (deletePattern.test(responseText)) {
      // If the AI confirms a task was deleted, we might need to refresh the task list
      return {
        isTaskIntent: true,
        operation: 'delete',
        description: responseText
      };
    }

    return { isTaskIntent: false };
  };

  // Helper function to create a new task via API
  const createTask = async (title: string, description: string) => {
    try {
      // Import the api here to avoid circular dependencies
      const { api } = await import('../../lib/api');

      const newTaskData = {
        title: title,
        description: description,
        completed: false
      };

      console.log('Creating task via API:', newTaskData);
      const createdTask = await api.post('/api/tasks', newTaskData);

      if (createdTask) {
        // Update the parent component's task list
        setTasks(prevTasks => [...prevTasks, createdTask]);

        // Show success in chat
        const successMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: `✓ Task "${title}" has been added successfully!`,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, successMessage]);
        return createdTask;
      }
    } catch (err) {
      console.error('Error creating task:', err);

      // Show error in chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `✗ Failed to add task: ${(err as Error).message || 'Unknown error'}`,
        sender: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);

      // Optionally set error in parent component
      if (setError) {
        setError('Failed to add task from chatbot. Please try again.');
      }
    }
  };

  // Helper function to detect task operations in user input before sending to chat API
  const detectTaskOperation = (userInput: string): {
    isTaskOperation: boolean;
    operation?: 'create' | 'delete' | 'update' | 'complete' | 'list' | 'summary';
    taskId?: number | string;
    title?: string;
    description?: string;
  } => {
    const lowerInput = userInput.toLowerCase().trim();

    // Detect task creation
    const createPattern = /^(?:add|create|make|new)\s+(?:a\s+)?(?:task|todo|to-do)\s+(?:to|called|named|about|regarding)?\s*(.+)$/i;
    if (createPattern.test(lowerInput)) {
      const match = createPattern.exec(userInput);
      if (match && match[1]) {
        let title = match[1].trim();
        // Clean up the title
        const titleEnd = title.indexOf('.') !== -1 ? title.indexOf('.') : title.length;
        title = title.substring(0, titleEnd).trim();
        title = title.replace(/^(?:to|for|about|regarding)\s+/, '');

        return {
          isTaskOperation: true,
          operation: 'create',
          title: title.charAt(0).toUpperCase() + title.slice(1)
        };
      }
    }

    // Detect task deletion - Updated to handle both integer and UUID patterns
    const deletePattern = /^(?:delete|remove|del)\s+(?:task\s+)?(\d+|[a-fA-F0-9\-]+)(?:\s+(.+))?$/i;
    if (deletePattern.test(lowerInput)) {
      const match = deletePattern.exec(userInput);
      if (match && match[1]) {
        return {
          isTaskOperation: true,
          operation: 'delete',
          taskId: match[1],
          description: match[2]?.trim() || ''
        };
      }
    }

    // Detect task completion - Updated to handle both integer and UUID patterns
    const completePattern = /^(?:complete|finish|done|mark.*complete)\s+(?:task\s+)?(\d+|[a-fA-F0-9\-]+)(?:\s+(.+))?$/i;
    if (completePattern.test(lowerInput)) {
      const match = completePattern.exec(userInput);
      if (match && match[1]) {
        return {
          isTaskOperation: true,
          operation: 'complete',
          taskId: match[1],
          description: match[2]?.trim() || ''
        };
      }
    }

    // Detect task listing
    const listPattern = /^(?:list|show|display|get)\s+(?:all\s+)?(?:my\s+)?(?:tasks|task)/i;
    if (listPattern.test(lowerInput)) {
      return {
        isTaskOperation: true,
        operation: 'list'
      };
    }

    // Detect task summary
    const summaryPattern = /^(?:summarize|summary|stats|statistics|overview|report)\s+(?:of\s+)?(?:my\s+)?(?:tasks|task)/i;
    if (summaryPattern.test(lowerInput)) {
      return {
        isTaskOperation: true,
        operation: 'summary'
      };
    }

    // Detect task update - Updated to handle both integer and UUID patterns
    const updatePattern = /^(?:update|change|modify|edit)\s+(?:task\s+)?(\d+|[a-fA-F0-9\-]+)\s+(?:to|with|as)\s+(.+)$/i;
    if (updatePattern.test(lowerInput)) {
      const match = updatePattern.exec(userInput);
      if (match && match[1] && match[2]) {
        return {
          isTaskOperation: true,
          operation: 'update',
          taskId: match[1],
          title: match[2].trim()
        };
      }
    }

    return { isTaskOperation: false };
  };

  // Helper function to resolve taskId (could be index or UUID)
  const resolveTaskId = (taskId: number | string): string | null => {
    // First, check if it's already a UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (uuidRegex.test(taskId.toString())) {
      return taskId.toString();
    }

    // If it's a number, treat it as an index (1-based) and find the corresponding task
    const taskIndex = parseInt(taskId.toString());
    if (!isNaN(taskIndex) && taskIndex > 0) {
      const indexedTask = tasks[taskIndex - 1]; // Convert to 0-based index
      if (indexedTask) {
        return indexedTask.id;
      }
    }

    // If we can't resolve it, return null
    return null;
  };

  // Helper function to handle task deletion
  const deleteTask = async (taskId: number | string) => {
    try {
      const { api } = await import('../../lib/api');

      // Resolve the actual task ID (could be index or UUID)
      const resolvedTaskId = resolveTaskId(taskId);
      if (!resolvedTaskId) {
        throw new Error(`Task with ID/index ${taskId} not found`);
      }

      // Find the task to get its details for messaging
      const taskToDelete = tasks.find(t => t.id === resolvedTaskId);
      const taskTitle = taskToDelete ? taskToDelete.title : `task ${resolvedTaskId}`;

      console.log('Deleting task via API:', resolvedTaskId);
      const result = await api.delete(`/api/tasks/${resolvedTaskId}`);

      if (result && result.success !== false) {
        // Update the parent component's task list
        setTasks(prevTasks => prevTasks.filter(task =>
          task.id !== resolvedTaskId
        ));

        // Show success in chat
        const successMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: `✓ Task "${taskTitle}" has been deleted successfully!`,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, successMessage]);
        return true;
      }
    } catch (err) {
      console.error('Error deleting task:', err);

      // Show error in chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `✗ Failed to delete task: ${(err as Error).message || 'Unknown error'}`,
        sender: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);

      if (setError) {
        setError('Failed to delete task from chatbot. Please try again.');
      }
      return false;
    }
  };

  // Helper function to handle task completion
  const toggleTaskCompletion = async (taskId: number | string) => {
    try {
      const { api } = await import('../../lib/api');

      // Resolve the actual task ID (could be index or UUID)
      const resolvedTaskId = resolveTaskId(taskId);
      if (!resolvedTaskId) {
        throw new Error(`Task with ID/index ${taskId} not found`);
      }

      // Find the task to get its details
      const taskToToggle = tasks.find(t => t.id === resolvedTaskId);
      const taskTitle = taskToToggle ? taskToToggle.title : `task ${resolvedTaskId}`;

      console.log('Toggling task completion via API:', resolvedTaskId);
      const updatedTask = await api.patch(`/api/tasks/${resolvedTaskId}/toggle`, {});

      if (updatedTask) {
        // Update the parent component's task list
        setTasks(prevTasks => prevTasks.map(task =>
          task.id === resolvedTaskId ? updatedTask : task
        ));

        // Show success in chat
        const status = updatedTask.completed ? 'completed' : 'marked as incomplete';
        const successMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: `✓ Task "${taskTitle}" has been ${status}!`,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, successMessage]);
        return true;
      }
    } catch (err) {
      console.error('Error toggling task completion:', err);

      // Show error in chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `✗ Failed to update task: ${(err as Error).message || 'Unknown error'}`,
        sender: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);

      if (setError) {
        setError('Failed to update task from chatbot. Please try again.');
      }
      return false;
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputMessage.trim()) return;

    console.log('Sending message:', inputMessage);

    // Add user message to the chat
    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputMessage,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    // Don't clear input yet if it's a task operation
    const currentInput = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    try {
      // Check if this is a direct task operation
      const taskOp = detectTaskOperation(currentInput);

      if (taskOp.isTaskOperation) {
        console.log('Detected task operation:', taskOp);

        switch (taskOp.operation) {
          case 'create':
            if (taskOp.title) {
              await createTask(taskOp.title, currentInput);
            }
            break;

          case 'delete':
            if (taskOp.taskId) {
              await deleteTask(taskOp.taskId);
            }
            break;

          case 'complete':
            if (taskOp.taskId) {
              await toggleTaskCompletion(taskOp.taskId);
            }
            break;

          case 'list':
            // Call the direct API to get tasks
            try {
              const { api } = await import('../../lib/api');
              const taskList = await api.get('/api/tasks');

              if (taskList && Array.isArray(taskList) && taskList.length > 0) {
                const taskDescriptions = taskList.map(task =>
                  `${task.id}: ${task.title} [${task.completed ? 'Completed' : 'Pending'}]`
                ).join('\n');

                const listResponse = `Here are your tasks:\n${taskDescriptions}`;

                const assistantMessage: Message = {
                  id: (Date.now() + 1).toString(),
                  text: listResponse,
                  sender: 'assistant',
                  timestamp: new Date(),
                };

                setMessages(prev => [...prev, assistantMessage]);
              } else {
                const assistantMessage: Message = {
                  id: (Date.now() + 1).toString(),
                  text: 'You have no tasks yet.',
                  sender: 'assistant',
                  timestamp: new Date(),
                };

                setMessages(prev => [...prev, assistantMessage]);
              }
            } catch (err) {
              console.error('Error listing tasks:', err);
              const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: `✗ Failed to list tasks: ${(err as Error).message || 'Unknown error'}`,
                sender: 'assistant',
                timestamp: new Date(),
              };

              setMessages(prev => [...prev, errorMessage]);
              if (setError) {
                setError('Failed to list tasks from chatbot. Please try again.');
              }
            }
            break;

          case 'update':
            // Call the direct API to update task
            if (taskOp.taskId && taskOp.title) {
              try {
                const { api } = await import('../../lib/api');

                // Resolve the actual task ID (could be index or UUID)
                const resolvedTaskId = resolveTaskId(taskOp.taskId);
                if (!resolvedTaskId) {
                  throw new Error(`Task with ID/index ${taskOp.taskId} not found`);
                }

                // Find the task to get its details for messaging
                const taskToUpdate = tasks.find(t => t.id === resolvedTaskId);
                const oldTitle = taskToUpdate ? taskToUpdate.title : `task ${resolvedTaskId}`;

                const updatedTask = await api.put(`/api/tasks/${resolvedTaskId}`, {
                  title: taskOp.title,
                  description: taskOp.description || (taskToUpdate ? taskToUpdate.description : '')
                });

                if (updatedTask) {
                  // Update the parent component's task list
                  setTasks(prevTasks => prevTasks.map(task =>
                    task.id === resolvedTaskId ? updatedTask : task
                  ));

                  // Show success in chat
                  const successMessage: Message = {
                    id: (Date.now() + 1).toString(),
                    text: `✓ Task "${oldTitle}" has been updated to "${taskOp.title}"!`,
                    sender: 'assistant',
                    timestamp: new Date(),
                  };

                  setMessages(prev => [...prev, successMessage]);
                }
              } catch (err) {
                console.error('Error updating task:', err);

                // Show error in chat
                const errorMessage: Message = {
                  id: (Date.now() + 1).toString(),
                  text: `✗ Failed to update task: ${(err as Error).message || 'Unknown error'}`,
                  sender: 'assistant',
                  timestamp: new Date(),
                };

                setMessages(prev => [...prev, errorMessage]);

                if (setError) {
                  setError('Failed to update task from chatbot. Please try again.');
                }
              }
            }
            break;

          case 'summary':
            // Call the direct API to get task summary
            try {
              const { api } = await import('../../lib/api');
              const taskList = await api.get('/api/tasks');

              if (taskList && Array.isArray(taskList)) {
                const totalTasks = taskList.length;
                const completedTasks = taskList.filter((task: any) => task.completed).length;
                const pendingTasks = totalTasks - completedTasks;

                const summaryResponse = `Task Summary:\nTotal: ${totalTasks}\nCompleted: ${completedTasks}\nPending: ${pendingTasks}`;

                const assistantMessage: Message = {
                  id: (Date.now() + 1).toString(),
                  text: summaryResponse,
                  sender: 'assistant',
                  timestamp: new Date(),
                };

                setMessages(prev => [...prev, assistantMessage]);
              } else {
                const assistantMessage: Message = {
                  id: (Date.now() + 1).toString(),
                  text: 'No tasks found to summarize.',
                  sender: 'assistant',
                  timestamp: new Date(),
                };

                setMessages(prev => [...prev, assistantMessage]);
              }
            } catch (err) {
              console.error('Error getting task summary:', err);
              const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                text: `✗ Failed to get task summary: ${(err as Error).message || 'Unknown error'}`,
                sender: 'assistant',
                timestamp: new Date(),
              };

              setMessages(prev => [...prev, errorMessage]);
              if (setError) {
                setError('Failed to get task summary from chatbot. Please try again.');
              }
            }
            break;

          default:
            // For other operations, send to chat API
            const defaultResponse = await chatApi.sendMessage(currentInput);
            const defaultSafeResponse = defaultResponse.message || 'Processed your request.';

            const defaultAssistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              text: defaultSafeResponse,
              sender: 'assistant',
              timestamp: new Date(),
            };

            setMessages(prev => [...prev, defaultAssistantMessage]);
            break;
        }
      } else {
        // Not a task operation, send to chat API as usual
        const response = await chatApi.sendMessage(currentInput);
        console.log('Received response from chat API:', response);

        // Create assistant message based on response status
        // Ensure the response message is never empty - avoid the specific fallback message
        const safeResponseText = response.message || 'I processed your request and here\'s the response from the AI assistant.';

        // Check if this response indicates a task should be created
        const taskIntent = detectTaskIntent(safeResponseText);

        if (taskIntent.isTaskIntent && taskIntent.title) {
          console.log('Detected task intent from AI response:', taskIntent);

          // First add the assistant's response to the chat
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(), // Ensure unique ID
            text: safeResponseText,
            sender: 'assistant',
            timestamp: new Date(),
          };

          setMessages(prev => [...prev, assistantMessage]);

          // Then create the task
          await createTask(taskIntent.title, taskIntent.description || currentInput);
        } else {
          // Just add the assistant's response normally
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(), // Ensure unique ID
            text: safeResponseText,
            sender: 'assistant',
            timestamp: new Date(),
          };

          console.log('Adding assistant message:', safeResponseText);

          // Add the assistant message to the chat
          setMessages(prev => [...prev, assistantMessage]);
        }
      }
    } catch (error) {
      console.error('Chat API error:', error);
      // Handle error with a friendly message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an issue. Please try again.',
        sender: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to handle quick action button clicks
  const handleQuickAction = (action: string) => {
    setInputMessage(action);
    // Trigger the same handler as the form submission
    const mockEvent = {
      preventDefault: () => {}
    } as React.FormEvent;
    handleSendMessage(mockEvent);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow">
      {/* Chat Header */}
      <div className="bg-gray-800 text-white p-4 rounded-t-lg">
        <h2 className="text-lg font-semibold">AI Assistant</h2>
      </div>

      {/* Quick Actions Section */}
      <div className="p-4 border-b bg-gray-50">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Quick Actions</h3>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleQuickAction('Add a new task')}
            className="px-3 py-1 text-xs bg-indigo-100 text-indigo-800 rounded-md hover:bg-indigo-200 transition-colors"
          >
            Add task
          </button>
          <button
            type="button"
            onClick={() => handleQuickAction('List all my tasks')}
            className="px-3 py-1 text-xs bg-green-100 text-green-800 rounded-md hover:bg-green-200 transition-colors"
          >
            List tasks
          </button>
          <button
            type="button"
            onClick={() => handleQuickAction('Complete task 1')}
            className="px-3 py-1 text-xs bg-blue-100 text-blue-800 rounded-md hover:bg-blue-200 transition-colors"
          >
            Complete task
          </button>
          <button
            type="button"
            onClick={() => handleQuickAction('Update task 1 with new description')}
            className="px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-md hover:bg-yellow-200 transition-colors"
          >
            Update task
          </button>
          <button
            type="button"
            onClick={() => handleQuickAction('Delete task 1')}
            className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded-md hover:bg-red-200 transition-colors"
          >
            Delete task
          </button>
          <button
            type="button"
            onClick={() => handleQuickAction('Show task summary')}
            className="px-3 py-1 text-xs bg-purple-100 text-purple-800 rounded-md hover:bg-purple-200 transition-colors"
          >
            Task summary
          </button>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-96">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 italic py-8">
            Start a conversation with the AI assistant...
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-800'
                }`}
              >
                <div className="text-sm">{message.text}</div>
                <div
                  className={`text-xs mt-1 ${
                    message.sender === 'user' ? 'text-blue-200' : 'text-gray-500'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 max-w-xs px-4 py-2 rounded-lg">
              <div className="text-sm">Thinking...</div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="p-4 border-t">
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            className={`px-4 py-2 rounded-md text-white ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600'
            }`}
            disabled={isLoading || !inputMessage.trim()}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}