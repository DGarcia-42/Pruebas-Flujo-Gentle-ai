import { getToken } from '../auth/storage';

export interface ApiError {
  detail: string;
}

/**
 * Central fetch wrapper.
 *
 * - Attaches `Authorization: Bearer <token>` when a token is in storage.
 * - Parses JSON responses automatically.
 * - Returns `null` for 204 No Content.
 * - Throws an `ApiError`-shaped object on non-2xx responses.
 *
 * All paths are relative (`/api/...`) — the Vite dev proxy forwards them
 * to `http://127.0.0.1:8000`. In production, same-origin serving keeps
 * relative paths working without CORS configuration.
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T | null> {
  const token = getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(path, { ...options, headers });

  if (response.status === 204) {
    return null;
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail =
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      typeof (body as ApiError).detail === 'string'
        ? (body as ApiError).detail
        : `HTTP ${response.status}`;

    throw { detail } as ApiError;
  }

  return body as T;
}

// ---------------------------------------------------------------------------
// Typed helpers for the auth endpoints
// ---------------------------------------------------------------------------

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  username: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export function register(data: RegisterRequest): Promise<RegisterResponse | null> {
  return apiFetch<RegisterResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function login(data: LoginRequest): Promise<LoginResponse | null> {
  return apiFetch<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
