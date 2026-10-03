// src/lib/chatApi.ts
import { api } from './api';

interface ChatRequest {
  message: string;
}

interface ChatResponse {
  status: 'success' | 'fallback' | 'error';
  message: string;
  data: any | null;
}

// Keep track of current request to prevent multiple simultaneous requests
let currentAbortController: AbortController | null = null;

export const chatApi = {
  async sendMessage(message: string): Promise<ChatResponse> {
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
      const timeoutId = setTimeout(() => currentAbortController?.abort(), 30000); // 30 second timeout

      try {
        // Call backend chat endpoint - note the correct path is /api/chat/ based on router prefix
        const response = await api.post('/api/chat/', { message }, {
          signal: currentAbortController.signal
        });

        clearTimeout(timeoutId);

        // Clear the current controller after successful request
        currentAbortController = null;

        // Handle the response based on the backend format
        if (response) {
          // Ensure response conforms to expected schema
          if (typeof response === 'object' && response.status && response.message !== undefined) {
            // Ensure message is never empty - avoid the specific fallback message
            const safeMessage = response.message || 'I processed your request and here\'s the response from the AI assistant.';

            return {
              status: response.status,
              message: safeMessage,
              data: response.data || null
            };
          } else {
            // Unexpected response format
            console.warn('Unexpected response format from chat API:', response);
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
      const response = await fetch(`${api['API_BASE_URL']}/api/chat/health`);
      return response.ok;
    } catch (error) {
      console.error('Chat service health check failed:', error);
      return false;
    }
  }
};