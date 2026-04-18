export type AIProvider = "deepseek" | "siliconflow" | "custom";

export interface AIConfig {
  provider: AIProvider;
  apiKey: string;
  model: string;
  baseUrl: string;
}

const KEYS = {
  provider: "fhr_ai_provider",
  apiKey: "fhr_ai_api_key",
  model: "fhr_ai_model",
  baseUrl: "fhr_ai_base_url",
} as const;

export const PROVIDER_PRESETS: Record<AIProvider, { label: string; model: string; baseUrl: string }> = {
  deepseek: { label: "DeepSeek", model: "deepseek-chat", baseUrl: "https://api.deepseek.com/v1" },
  siliconflow: { label: "SiliconFlow", model: "Qwen/Qwen2.5-72B-Instruct", baseUrl: "https://api.siliconflow.cn/v1" },
  custom: { label: "自定义 (OpenAI 兼容)", model: "", baseUrl: "" },
};

const DEFAULT: AIConfig = {
  provider: "deepseek",
  apiKey: "",
  model: "deepseek-chat",
  baseUrl: "https://api.deepseek.com/v1",
};

export function getAIConfig(): AIConfig {
  if (typeof window === "undefined") return DEFAULT;
  return {
    provider: (localStorage.getItem(KEYS.provider) as AIProvider) ?? DEFAULT.provider,
    apiKey: localStorage.getItem(KEYS.apiKey) ?? DEFAULT.apiKey,
    model: localStorage.getItem(KEYS.model) ?? DEFAULT.model,
    baseUrl: localStorage.getItem(KEYS.baseUrl) ?? DEFAULT.baseUrl,
  };
}

export function setAIConfig(patch: Partial<AIConfig>): void {
  if (typeof window === "undefined") return;
  if (patch.provider != null) localStorage.setItem(KEYS.provider, patch.provider);
  if (patch.apiKey != null) localStorage.setItem(KEYS.apiKey, patch.apiKey);
  if (patch.model != null) localStorage.setItem(KEYS.model, patch.model);
  if (patch.baseUrl != null) localStorage.setItem(KEYS.baseUrl, patch.baseUrl);
}
