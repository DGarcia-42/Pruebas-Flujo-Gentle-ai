/**
 * In-memory token storage seam.
 *
 * Token is intentionally lost on page reload (not persisted to
 * localStorage or sessionStorage). This is a deliberate tradeoff for
 * XSS resistance: a JS-accessible store can be read by injected scripts.
 *
 * The single module-level variable is the only place in the app that
 * holds the token. All callers go through these three functions.
 */

let _token: string | null = null;

export function setToken(token: string): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export function clearToken(): void {
  _token = null;
}
