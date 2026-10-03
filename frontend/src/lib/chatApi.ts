// src/lib/chatApi.ts
import { api } from './api';

export interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

// Browser-local "YYYY-MM-DDTHH:MM" so the bot resolves "tomorrow" in the user's timezone
function localNow(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

interface ChatResponse {
  status: 'success' | 'fallback' | 'error';
  message: string;
  data: any | null;
}

// Keep track of current request to prevent multiple simultaneous requests
let currentAbortController: AbortController | null = null;

export const chatApi = {
  async sendMessage(message: string, history: ChatHistoryItem[] = []): Promise<ChatResponse> {
    // Cancel any existing request to prevent multiple simultaneous requests
    if (currentAbortController) {
      currentAbortController.abort();
    }

    try {
      // Validate input
      if (!message || !message.trim()) {
        return {
          status: 'error',
          message: 'Message cannot be empty',
          data: null
        };
      }

      // Create new AbortController for this request
      currentAbortController = new AbortController();
      // Tool-using replies can take several model round trips
      const timeoutId = setTimeout(() => currentAbortController?.abort(), 60000);

      try {
        // Call backend chat endpoint - note the correct path is /api/chat/ based on router prefix
        // We need to use fetch directly to support the AbortSignal since api.post doesn't support options
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const token = localStorage.getItem('token');

        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };

        const response = await fetch(`${API_BASE_URL}/api/chat/`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ message, history, client_now: localNow() }),
          signal: currentAbortController.signal
        });

        // Expired or invalid token: same handling as api.request
        if (response.status === 401) {
          clearTimeout(timeoutId);
          currentAbortController = null;
          localStorage.removeItem('token');
          window.location.href = '/login';
          return {
            status: 'fallback',
            message: 'Authentication required. Please log in again.',
            data: null
          };
        }

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Request failed with status ${response.status}: ${errorText}`);
        }

        const responseData = await response.json();

        clearTimeout(timeoutId);

        // Clear the current controller after successful request
        currentAbortController = null;

        // Handle the response based on the backend format
        if (responseData) {
          // Ensure response conforms to expected schema
          if (typeof responseData === 'object' && responseData.status && responseData.message !== undefined) {
            // Ensure message is never empty - avoid the specific fallback message
            const safeMessage = responseData.message || 'I processed your request and here\'s the response from the AI assistant.';

            return {
              status: responseData.status,
              message: safeMessage,
              data: responseData.data || null
            };
          } else {
            // Unexpected response format
            console.warn('Unexpected response format from chat API:', responseData);
            return {
              status: 'error',
              message: 'Received unexpected response format from the server.',
              data: null
            };
          }
        } else {
          // Fallback if response is null (unauthorized scenario)
          return {
            status: 'fallback',
            message: 'Authentication required. Please log in again.',
            data: null
          };
        }
      } catch (abortError) {
        clearTimeout(timeoutId);

        // Clear the current controller after the request completes (even if failed)
        currentAbortController = null;

        if ((abortError as Error).name === 'AbortError') {
          console.error('Chat API request timed out');
          return {
            status: 'error',
            message: 'The request took too long to complete. Please try again.',
            data: null
          };
        }

        throw abortError; // Re-throw if it's not an AbortError
      }
    } catch (error) {
      // Clear the current controller in case of any error
      currentAbortController = null;

      console.error('Chat API error:', error);

      // Check if it's a network error
      if (error instanceof TypeError && (error as any).message.includes('fetch')) {
        return {
          status: 'error',
          message: 'Unable to connect to the chat service. Please ensure the backend server is running.',
          data: null
        };
      }

      // Return a friendly error message instead of showing raw errors
      return {
        status: 'error',
        message: 'Unable to connect to the chat service. Please check your connection and try again.',
        data: null
      };
    }
  },

  // Method to cancel any ongoing request
  cancelCurrentRequest() {
    if (currentAbortController) {
      currentAbortController.abort();
      currentAbortController = null;
    }
  },

  // Health check for the chat service
  async healthCheck(): Promise<boolean> {
    try {
      // Use the same base URL pattern as in api.ts
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/chat/health`);
      return response.ok;
    } catch (error) {
      console.error('Chat service health check failed:', error);
      return false;
    }
  }
};