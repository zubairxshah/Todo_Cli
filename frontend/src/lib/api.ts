// src/lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// A sleeping free-tier backend can take close to a minute to wake up
const REQUEST_TIMEOUT_MS = 90000;

/** Error carrying the backend's message (FastAPI's `detail`) and HTTP status. */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`;
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') message = body.detail;
    else if (Array.isArray(body?.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
  } catch {
    /* not JSON */
  }
  return new ApiError(message, response.status);
}

export const api = {
  async request(endpoint: string, options: RequestInit = {}) {
    const token = localStorage.getItem('token');

    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      });

      // An expired session: drop the token and go to login. Failed logins and
      // signups also return 401, but those must show their error message instead.
      if (response.status === 401 && token && !endpoint.startsWith('/api/auth/')) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        return null;
      }

      return response;
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        throw new ApiError('The server took too long to respond. It may be waking up; please try again.', 0);
      }
      throw new ApiError('Cannot reach the server. Check your connection and try again.', 0);
    } finally {
      clearTimeout(timeoutId);
    }
  },

  async get(endpoint: string) {
    const response = await this.request(endpoint, { method: 'GET' });
    if (!response) return null;
    if (!response.ok) throw await errorFromResponse(response);
    return response.json();
  },

  async post(endpoint: string, data: any) {
    const response = await this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (!response) return null;
    if (!response.ok) throw await errorFromResponse(response);

    const responseBody = await response.text();
    return responseBody.trim() ? JSON.parse(responseBody) : {};
  },

  async put(endpoint: string, data: any) {
    const response = await this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (!response) return null;
    if (!response.ok) throw await errorFromResponse(response);
    return response.json();
  },

  async patch(endpoint: string, data: any) {
    const response = await this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    if (!response) return null;
    if (!response.ok) throw await errorFromResponse(response);
    return response.json();
  },

  async delete(endpoint: string) {
    const response = await this.request(endpoint, { method: 'DELETE' });
    if (!response) return null;
    if (!response.ok) throw await errorFromResponse(response);
    return { success: true };
  },
};
