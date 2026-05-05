/**
 * Runtime helpers for resolving the backend API URL.
 *
 * - getPublicApiUrl()  → used in client components (reads NEXT_PUBLIC_API_URL)
 * - getServerApiUrl()  → used in API route handlers (reads API_URL, falls back to NEXT_PUBLIC_API_URL)
 */

export function getPublicApiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  return url.replace(/\/+$/, '');
}

export function getServerApiUrl(): string {
  const url = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  return url.replace(/\/+$/, '');
}
