import { getApiBase } from "./settings";

function API_BASE() {
  return getApiBase();
}

// ---------------------------------------------------------------------------
// LLM header helpers
// ---------------------------------------------------------------------------

/** Build per-request override headers from the given AI config (from the settings modal). */
function buildLLMHeaders(cfg: { apiKey: string; model: string; baseUrl: string }): Record<string, string> {
  if (!cfg.apiKey.trim()) return {};
  const headers: Record<string, string> = {
    "x-llm-api-key": cfg.apiKey.trim(),
    "x-llm-model": cfg.model.trim(),
  };
  if (cfg.baseUrl.trim()) headers["x-llm-base-url"] = cfg.baseUrl.trim();
  return headers;
}

/** Read stored AI config and return request headers (empty object when no API key saved). */
function getLLMHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  // Lazy import avoids SSR issues
  const apiKey = localStorage.getItem("fhr_ai_api_key") ?? "";
  const model = localStorage.getItem("fhr_ai_model") ?? "";
  const baseUrl = localStorage.getItem("fhr_ai_base_url") ?? "";
  return buildLLMHeaders({ apiKey, model, baseUrl });
}

export interface Citation {
  idx: number;
  type: "law" | "case";
  chunk_id: string;
  label: string;
}

export interface Ref {
  idx: number;
  kind: "law" | "case";
  chunk_id: string;
  label: string;
}

export interface ChatResponse {
  text: string;
  citations: Citation[];
  refs: Ref[];
  oob_count: number;
}

export interface Chunk {
  id: string;
  kind: "law" | "case";
  label: string;
  text: string;
  source_url: string | null;
  extra: Record<string, unknown>;
}

export async function postChat(content: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE()}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getLLMHeaders(),
    },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<ChatResponse>;
}

export interface TestAIResult {
  ok: boolean;
  text?: string;
  error?: string;
}

/**
 * Send a lightweight test prompt to verify the AI config.
 * Accepts the config directly so callers can test before saving to localStorage.
 */
export async function testAIConfig(
  base: string,
  cfg: { apiKey: string; model: string; baseUrl: string },
): Promise<TestAIResult> {
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/api/chat/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildLLMHeaders(cfg),
      },
      signal: AbortSignal.timeout(20_000),
    });
    if (!res.ok) {
      return { ok: false, error: `HTTP ${res.status}` };
    }
    return res.json() as Promise<TestAIResult>;
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}

export async function getChunk(chunkId: string): Promise<Chunk> {
  const res = await fetch(`${API_BASE()}/api/knowledge/chunks/${chunkId}`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<Chunk>;
}

export async function checkHealth(base: string): Promise<boolean> {
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/api/health`, {
      signal: AbortSignal.timeout(4000),
    });
    return res.ok;
  } catch {
    return false;
  }
}
