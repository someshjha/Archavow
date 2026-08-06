export type ChatProvider = "ollama" | "openai";
export type EmbeddingProvider = "ollama" | "openai" | "none";

export type AISettings = {
  chat_provider: ChatProvider;
  chat_model: string;
  embedding_provider: EmbeddingProvider;
  embedding_model: string;
  embedding_dimensions: number;
  ollama_base_url: string;
  openai_base_url: string;
  openai_api_key_configured: boolean;
};

export type AISettingsUpdate = Partial<{
  chat_provider: ChatProvider;
  chat_model: string;
  embedding_provider: EmbeddingProvider;
  embedding_model: string;
  embedding_dimensions: number;
  ollama_base_url: string;
  openai_base_url: string;
}>;

export type ProbeResult = {
  ok: boolean;
  reachable: boolean;
  provider: string;
  model: string | null;
  detail: string | null;
  dimensions: number | null;
};

export type ProjectLifecycle = {
  stage: "intake" | "interview" | "options" | "package" | "export";
  label: string;
  continue_path: string;
  milestones: {
    intake_done: boolean;
    interview_started: boolean;
    interview_ready: boolean;
    options_ready: boolean;
    option_selected: boolean;
    package_ready: boolean;
    export_done: boolean;
  };
};

export type Project = {
  id: string;
  name: string;
  description: string | null;
  stack_tags: string[];
  business_objective?: string | null;
  problem_statement?: string | null;
  preferred_cloud?: string | null;
  scale_availability?: string | null;
  tech_constraints?: string | null;
  lifecycle?: ProjectLifecycle | null;
};

export type ProjectCreate = {
  name: string;
  description?: string;
  stack_tags?: string[];
  business_objective?: string;
  problem_statement?: string;
  preferred_cloud?: string;
  scale_availability?: string;
  tech_constraints?: string;
};

export type ClarificationQuestion = {
  id: string;
  code: string;
  prompt: string;
  category: string;
  status: string;
  answer: string | null;
};

export type CompletenessCategory = {
  key: string;
  label: string;
  score: number;
  floor: number;
  closed: number;
  total: number;
  open_codes: string[];
  open_labels: string[];
};

export type UnlockCheck = {
  key: string;
  label: string;
  value: number;
  target: number;
  ok: boolean;
};

export type Completeness = {
  overall: number;
  scope: number;
  story_readiness: number;
  reliability: number;
  security_compliance: number;
  delivery: number;
  categories: CompletenessCategory[];
  ready: boolean;
  unlock: UnlockCheck[];
  gaps: string[];
  captured: string[];
};

export type NextImpact = {
  code: string;
  category_key: string;
  category_label: string;
  category_from: number;
  category_to: number;
  overall_from: number;
  overall_to: number;
};

export type InterviewState = {
  questions: ClarificationQuestion[];
  completeness: Completeness;
  active_question: ClarificationQuestion | null;
  next_impact?: NextImpact | null;
  ai_assist?: { status: string; detail?: string | null };
  intro?: string | null;
  ai_reply?: string | null;
};

function apiBase(): string {
  return (
    process.env.ARCHAVOW_API_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (init?.headers) {
    new Headers(init.headers as HeadersInit).forEach((value, key) => {
      headers[key] = value;
    });
  }
  const hasAuth = Object.keys(headers).some((k) => k.toLowerCase() === "authorization");
  const serverKey = process.env.ARCHAVOW_API_KEY?.trim();
  // SSR / server actions call the API directly (not via /api/backend proxy).
  if (!hasAuth && serverKey && path.startsWith("/api/v1/")) {
    headers.Authorization = `Bearer ${serverKey}`;
  }

  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  // 204 / empty bodies (e.g. DELETE) have no JSON payload.
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export async function getAISettings(): Promise<AISettings> {
  const body = await api<{ data: AISettings }>("/api/v1/settings/ai");
  return body.data;
}

export async function patchAISettings(update: AISettingsUpdate): Promise<AISettings> {
  const body = await api<{ data: AISettings }>("/api/v1/settings/ai", {
    method: "PATCH",
    body: JSON.stringify(update),
  });
  return body.data;
}

export async function probeChat(): Promise<ProbeResult> {
  const body = await api<{ data: ProbeResult }>("/api/v1/settings/ai/probe/chat", {
    method: "POST",
  });
  return body.data;
}

export async function probeEmbeddings(): Promise<ProbeResult> {
  const body = await api<{ data: ProbeResult }>(
    "/api/v1/settings/ai/probe/embeddings",
    { method: "POST" },
  );
  return body.data;
}

export async function listProjects(): Promise<Project[]> {
  const body = await api<{ data: Project[] }>("/api/v1/projects");
  return body.data;
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  const body = await api<{ data: Project }>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return body.data;
}

export async function getProject(id: string): Promise<Project> {
  const body = await api<{ data: Project }>(`/api/v1/projects/${id}`);
  return body.data;
}

export async function deleteProject(id: string): Promise<void> {
  await api<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}

export async function getDashboard(projectId: string): Promise<unknown> {
  const body = await api<{ data: unknown }>(
    `/api/v1/projects/${projectId}/dashboard`,
  );
  return body.data;
}

export async function getPackage(projectId: string): Promise<unknown | null> {
  try {
    const body = await api<{ data: unknown }>(
      `/api/v1/projects/${projectId}/package`,
    );
    return body.data;
  } catch {
    return null;
  }
}

export async function getOptions(projectId: string): Promise<{
  options: { id: string; title: string; selected: boolean }[];
  selected_option_id: string | null;
}> {
  const body = await api<{
    data: {
      options: { id: string; title: string; selected: boolean }[];
      selected_option_id: string | null;
    };
  }>(`/api/v1/projects/${projectId}/options`);
  return body.data;
}

export async function analyzeInterview(projectId: string): Promise<InterviewState> {
  const body = await api<{ data: InterviewState }>(
    `/api/v1/projects/${projectId}/interview/analyze`,
    { method: "POST" },
  );
  return body.data;
}

export async function getInterview(projectId: string): Promise<InterviewState> {
  const body = await api<{ data: InterviewState }>(
    `/api/v1/projects/${projectId}/interview`,
  );
  return body.data;
}

export async function answerInterview(
  projectId: string,
  questionId: string,
  answer: string,
): Promise<InterviewState & { question: ClarificationQuestion }> {
  const body = await api<{
    data: InterviewState & { question: ClarificationQuestion };
  }>(`/api/v1/projects/${projectId}/interview/answer`, {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, answer }),
  });
  return body.data;
}

export async function getHealth(): Promise<{
  status: string;
  postgres: { ok: boolean; detail?: string };
  ai: Record<string, unknown>;
}> {
  return api("/health");
}
