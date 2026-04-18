import { getApiBase } from "./settings";

function API_BASE() {
  return getApiBase();
}

export type Status = "drafting" | "pending_review" | "approved";

export interface Profile {
  position: {
    title: string | null;
    department: string | null;
    report_to: string | null;
    headcount: number | null;
    location: string | null;
    start_date: string | null;
  };
  responsibilities: string[];
  hard_requirements: {
    education: string | null;
    years: string | null;
    skills: string[];
    industry: string | null;
  };
  soft_preferences: {
    bonus_points: string[];
    culture_fit: string | null;
    team_style: string | null;
  };
  compensation: {
    salary_range: string | null;
    level: string | null;
    employment_type: string | null;
  };
}

export interface MessageRead {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface JDRead {
  content_md: string;
  edited_content_md: string | null;
  generated_at: string;
  approved_at: string | null;
}

export interface RequestRead {
  id: string;
  title: string;
  status: Status;
  profile: Profile;
  missing_fields: string[];
  ready_for_jd: boolean;
  messages: MessageRead[];
  jd: JDRead | null;
  created_at: string;
  updated_at: string;
}

export interface RequestListItem {
  id: string;
  title: string;
  status: Status;
  updated_at: string;
}

export interface PostMessageResponse {
  assistant_message: MessageRead;
  profile: Profile;
  missing_fields: string[];
  ready_for_jd: boolean;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return (await res.json()) as T;
}

export async function createRequest(): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests`, { method: "POST" });
  return json<RequestRead>(res);
}

export async function listRequests(): Promise<RequestListItem[]> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests`);
  return json<RequestListItem[]>(res);
}

export async function getRequest(id: string): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}`);
  return json<RequestRead>(res);
}

export async function postMessage(id: string, content: string): Promise<PostMessageResponse> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return json<PostMessageResponse>(res);
}

export async function generateJD(id: string): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}/jd`, { method: "POST" });
  return json<RequestRead>(res);
}

export async function patchRequest(
  id: string,
  body: { edited_content_md?: string; action?: "approve" }
): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<RequestRead>(res);
}
