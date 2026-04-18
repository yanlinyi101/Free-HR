const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<ChatResponse>;
}

export async function getChunk(chunkId: string): Promise<Chunk> {
  const res = await fetch(`${API_BASE}/api/knowledge/chunks/${chunkId}`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<Chunk>;
}
