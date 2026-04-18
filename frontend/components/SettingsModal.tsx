"use client";

import { useEffect, useRef, useState } from "react";
import { getApiBase, setApiBase, DEFAULT_BASE } from "@/lib/settings";
import { checkHealth, testAIConfig } from "@/lib/api";
import {
  getAIConfig, setAIConfig, PROVIDER_PRESETS,
  type AIProvider, type AIConfig,
} from "@/lib/ai-settings";

type ConnStatus = "idle" | "checking" | "ok" | "error";
type Tab = "connection" | "model";

export default function SettingsModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("connection");

  // Connection tab
  const [apiUrl, setApiUrl] = useState("");
  const [connStatus, setConnStatus] = useState<ConnStatus>("idle");
  const urlInputRef = useRef<HTMLInputElement>(null);

  // AI model tab
  const [aiConfig, setLocalAIConfig] = useState<AIConfig>({ provider: "deepseek", apiKey: "", model: "deepseek-chat", baseUrl: "" });
  const [showKey, setShowKey] = useState(false);
  const [aiTestStatus, setAITestStatus] = useState<"idle" | "checking" | "ok" | "error">("idle");
  const [aiTestMsg, setAITestMsg] = useState("");

  useEffect(() => {
    setApiUrl(getApiBase());
    setLocalAIConfig(getAIConfig());
    if (tab === "connection") urlInputRef.current?.focus();

    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const testConnection = async () => {
    setConnStatus("checking");
    const ok = await checkHealth(apiUrl);
    setConnStatus(ok ? "ok" : "error");
  };

  const save = () => {
    setApiBase(apiUrl);
    setAIConfig(aiConfig);
    onClose();
  };

  const handleProviderChange = (provider: AIProvider) => {
    const preset = PROVIDER_PRESETS[provider];
    setLocalAIConfig((prev) => ({
      ...prev,
      provider,
      model: preset.model,
      baseUrl: preset.baseUrl,
    }));
    setAITestStatus("idle");
    setAITestMsg("");
  };

  const testAI = async () => {
    setAITestStatus("checking");
    setAITestMsg("");
    const base = getApiBase();
    const result = await testAIConfig(base, {
      apiKey: aiConfig.apiKey,
      model: aiConfig.model,
      baseUrl: aiConfig.baseUrl,
    });
    if (result.ok) {
      setAITestStatus("ok");
      setAITestMsg(result.text ? `模型回复：${result.text}` : "连接成功");
    } else {
      setAITestStatus("error");
      setAITestMsg(result.error ?? "未知错误");
    }
  };

  const statusConfig = {
    idle: { text: "", color: "text-gray-400" },
    checking: { text: "连接检测中…", color: "text-gray-400" },
    ok: { text: "✓ 连接正常", color: "text-green-600" },
    error: { text: "✗ 无法连接，请检查地址或后端服务", color: "text-red-500" },
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.35)", backdropFilter: "blur(4px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-lg mx-4 rounded-2xl shadow-2xl overflow-hidden"
        style={{ border: "1px solid rgba(0,0,0,0.08)", background: "#fff" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid #f0f0f0" }}>
          <h2 className="font-semibold text-gray-900 text-base">设置</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all"
            aria-label="关闭"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex px-6 pt-4 gap-1" style={{ borderBottom: "1px solid #f0f0f0" }}>
          {(["connection", "model"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="pb-3 px-3 text-sm font-medium transition-all relative"
              style={{
                color: tab === t ? "#2563eb" : "#6b7280",
                borderBottom: tab === t ? "2px solid #2563eb" : "2px solid transparent",
                marginBottom: "-1px",
              }}
            >
              {t === "connection" ? "连接设置" : "AI 模型"}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {tab === "connection" && (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                  后端服务地址
                </label>
                <div className="flex gap-2">
                  <input
                    ref={urlInputRef}
                    type="url"
                    value={apiUrl}
                    onChange={(e) => { setApiUrl(e.target.value); setConnStatus("idle"); }}
                    placeholder="http://localhost:8000"
                    className="flex-1 text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none transition-all focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                  />
                  <button
                    onClick={testConnection}
                    disabled={connStatus === "checking"}
                    className="text-sm px-4 py-2.5 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap transition-all font-medium"
                  >
                    测试连接
                  </button>
                </div>
                <p className={`text-xs mt-2 h-4 ${statusConfig[connStatus].color}`}>
                  {statusConfig[connStatus].text}
                </p>
              </div>
              <div
                className="rounded-xl px-4 py-3 text-xs text-gray-500 leading-relaxed"
                style={{ background: "#f8f9fa", border: "1px solid #f0f0f0" }}
              >
                修改地址后将在当前会话内立即生效，配置保存在浏览器本地（localStorage）。
              </div>
              <button
                onClick={() => { setApiUrl(DEFAULT_BASE); setConnStatus("idle"); }}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                重置为默认地址
              </button>
            </>
          )}

          {tab === "model" && (
            <>
              {/* Provider */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                  AI 提供商
                </label>
                <select
                  value={aiConfig.provider}
                  onChange={(e) => handleProviderChange(e.target.value as AIProvider)}
                  className="w-full text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 bg-white transition-all"
                >
                  {(Object.keys(PROVIDER_PRESETS) as AIProvider[]).map((key) => (
                    <option key={key} value={key}>{PROVIDER_PRESETS[key].label}</option>
                  ))}
                </select>
              </div>

              {/* Model name */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                  模型名称
                </label>
                <input
                  type="text"
                  value={aiConfig.model}
                  onChange={(e) => setLocalAIConfig((p) => ({ ...p, model: e.target.value }))}
                  placeholder="deepseek-chat"
                  className="w-full text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 font-mono transition-all"
                />
              </div>

              {/* API Key */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                  API Key
                </label>
                <div className="flex gap-2">
                  <input
                    type={showKey ? "text" : "password"}
                    value={aiConfig.apiKey}
                    onChange={(e) => setLocalAIConfig((p) => ({ ...p, apiKey: e.target.value }))}
                    placeholder="sk-..."
                    className="flex-1 text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 font-mono transition-all"
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="px-3.5 rounded-xl border border-gray-200 text-gray-500 hover:bg-gray-50 transition-all text-xs"
                  >
                    {showKey ? "隐藏" : "显示"}
                  </button>
                </div>
              </div>

              {/* Base URL (custom only) */}
              {aiConfig.provider === "custom" && (
                <div>
                  <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                    API Base URL
                  </label>
                  <input
                    type="url"
                    value={aiConfig.baseUrl}
                    onChange={(e) => setLocalAIConfig((p) => ({ ...p, baseUrl: e.target.value }))}
                    placeholder="https://api.openai.com/v1"
                    className="w-full text-sm border border-gray-200 rounded-xl px-4 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 font-mono transition-all"
                  />
                </div>
              )}

              {/* Test AI button */}
              <div className="flex items-center gap-3">
                <button
                  onClick={testAI}
                  disabled={aiTestStatus === "checking" || !aiConfig.apiKey.trim()}
                  className="text-sm px-4 py-2.5 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap transition-all font-medium"
                  title={!aiConfig.apiKey.trim() ? "请先填写 API Key" : ""}
                >
                  {aiTestStatus === "checking" ? "测试中…" : "测试 AI 连接"}
                </button>
                {aiTestStatus !== "idle" && (
                  <p
                    className="text-xs flex-1 truncate"
                    style={{
                      color: aiTestStatus === "ok" ? "#16a34a" : aiTestStatus === "error" ? "#ef4444" : "#9ca3af",
                    }}
                  >
                    {aiTestStatus === "ok" && "✓ "}
                    {aiTestStatus === "error" && "✗ "}
                    {aiTestStatus === "checking" ? "连接检测中…" : aiTestMsg}
                  </p>
                )}
              </div>

              {/* Note */}
              <div
                className="rounded-xl px-4 py-3 text-xs text-gray-500 leading-relaxed"
                style={{ background: "#f0f9ff", border: "1px solid #e0f2fe" }}
              >
                <strong className="text-blue-700">提示：</strong>
                API Key 保存在本地浏览器（localStorage），每次请求时通过请求头发送给后端。若此处留空，后端将使用服务器 <code className="bg-blue-100 px-1 rounded text-blue-700">.env</code> 中配置的密钥。
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-end gap-3 px-6 py-4"
          style={{ borderTop: "1px solid #f0f0f0" }}
        >
          <button
            onClick={onClose}
            className="text-sm px-5 py-2.5 rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 font-medium transition-all"
          >
            取消
          </button>
          <button
            onClick={save}
            className="text-sm px-5 py-2.5 rounded-xl text-white font-medium transition-all"
            style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
          >
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}
