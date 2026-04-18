"use client";

import { useEffect, useRef, useState } from "react";
import { getApiBase, setApiBase, DEFAULT_BASE } from "@/lib/settings";
import { checkHealth } from "@/lib/api";

type Status = "idle" | "checking" | "ok" | "error";

const NOTE = "配置保存在浏览器本地（localStorage），不会上传到服务器。";

export default function SettingsModal({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setUrl(getApiBase());
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const test = async (target: string) => {
    setStatus("checking");
    const ok = await checkHealth(target);
    setStatus(ok ? "ok" : "error");
  };

  const save = () => {
    setApiBase(url);
    onClose();
  };

  const reset = () => {
    setUrl(DEFAULT_BASE);
    setStatus("idle");
  };

  const statusLabel: Record<Status, string> = {
    idle: "",
    checking: "检测中…",
    ok: "连接正常 ✓",
    error: "无法连接 ✗",
  };
  const statusColor: Record<Status, string> = {
    idle: "text-gray-400",
    checking: "text-gray-400",
    ok: "text-green-600",
    error: "text-red-500",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md mx-4 bg-white rounded-2xl shadow-xl border border-gray-200 p-6">
        {/* title */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold text-gray-900 text-base">API 设置</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        {/* backend url */}
        <label className="block text-xs font-medium text-gray-500 mb-1.5">
          后端地址
          <span className="ml-1 text-gray-400 font-normal">(Free-HR 服务器)</span>
        </label>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setStatus("idle"); }}
            placeholder="http://localhost:8000"
            className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            onClick={() => test(url)}
            disabled={status === "checking"}
            className="text-sm px-3 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap"
          >
            测试
          </button>
        </div>
        <p className={`text-xs mt-1.5 h-4 ${statusColor[status]}`}>
          {statusLabel[status]}
        </p>

        {/* divider + note */}
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-400 leading-relaxed">
            <span className="font-medium text-gray-500">说明：</span>
            AI 模型（DeepSeek）和向量嵌入（SiliconFlow）的 API Key 配置在后端 <code className="bg-gray-100 px-1 rounded text-gray-600">.env</code> 文件中，不在此处设置。
          </p>
          <p className="text-xs text-gray-400 mt-1.5">{NOTE}</p>
        </div>

        {/* actions */}
        <div className="flex items-center justify-between mt-5">
          <button
            onClick={reset}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            重置为默认值
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={save}
              className="text-sm px-4 py-2 rounded-lg bg-blue-700 text-white hover:bg-blue-800"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
