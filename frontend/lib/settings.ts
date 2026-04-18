const STORAGE_KEY = "free_hr_api_base";
const DEFAULT_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function getApiBase(): string {
  if (typeof window === "undefined") return DEFAULT_BASE;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_BASE;
}

export function setApiBase(url: string): void {
  const trimmed = url.trim().replace(/\/$/, "");
  if (trimmed) {
    localStorage.setItem(STORAGE_KEY, trimmed);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function resetApiBase(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export { DEFAULT_BASE };
