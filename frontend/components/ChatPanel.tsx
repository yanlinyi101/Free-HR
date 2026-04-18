"use client";

import { useEffect, useRef } from "react";
import { Message } from "./MessageList";
import MessageBubble from "./MessageBubble";
import { Citation } from "@/lib/api";
import { useTypewriter } from "@/lib/typewriter"; // eslint-disable-line @typescript-eslint/no-unused-vars
import { getAIConfig } from "@/lib/ai-settings";
import { useState } from "react";

const SAMPLE_PROMPTS = [
  "员工严重违反规章制度可以直接解除吗？",
  "试用期可以不签劳动合同吗？",
  "经济补偿金如何计算？",
];

interface ChatPanelProps {
  messages: Message[];
  inputValue: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  onCitationClick: (chunkId: string) => void;
  onPromptClick: (prompt: string) => void;
}

function ModelBadge() {
  const [model, setModel] = useState("");
  useEffect(() => {
    setModel(getAIConfig().model || "deepseek-chat");
  }, []);
  return (
    <span
      className="text-[10px] px-2 py-0.5 rounded-full font-mono font-medium"
      style={{ background: "rgba(37,99,235,0.08)", color: "#2563eb", border: "1px solid rgba(37,99,235,0.15)" }}
    >
      {model}
    </span>
  );
}

function EmptyChat({ onPromptClick }: { onPromptClick: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-5 text-center">
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center mb-4 text-white font-bold text-lg"
        style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
      >
        F
      </div>
      <p className="text-sm font-medium text-gray-700 mb-1">AI 法律咨询</p>
      <p className="text-xs text-gray-400 mb-6 leading-relaxed max-w-[220px]">
        基于中国劳动法、劳动合同法等法规
      </p>
      <div className="w-full space-y-2">
        {SAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => onPromptClick(p)}
            className="w-full text-left px-3.5 py-2.5 rounded-xl text-xs text-gray-600 transition-all duration-150"
            style={{ border: "1px solid #e5e7eb", background: "#fff" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = "#93c5fd";
              (e.currentTarget as HTMLButtonElement).style.background = "#eff6ff";
              (e.currentTarget as HTMLButtonElement).style.color = "#2563eb";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = "#e5e7eb";
              (e.currentTarget as HTMLButtonElement).style.background = "#fff";
              (e.currentTarget as HTMLButtonElement).style.color = "#4b5563";
            }}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatPanel({
  messages,
  inputValue,
  onChange,
  onSubmit,
  isLoading,
  onCitationClick,
  onPromptClick,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [inputValue]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (inputValue.trim() && !isLoading) onSubmit();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full bg-white overflow-hidden">
      {/* Header */}
      <div
        className="shrink-0 px-5 py-3.5 flex items-center justify-between"
        style={{ borderBottom: "1px solid #f0f0f0" }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: "#22c55e", boxShadow: "0 0 0 2px rgba(34,197,94,0.2)" }}
          />
          <span className="text-sm font-semibold text-gray-800">AI 法律咨询</span>
        </div>
        <ModelBadge />
      </div>

      {/* Messages or empty */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <EmptyChat onPromptClick={onPromptClick} />
        ) : (
          <div className="px-4 py-5">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                role={msg.role}
                text={msg.text}
                citations={msg.citations as Citation[] | undefined}
                isLoading={msg.isLoading}
                onCitationClick={onCitationClick}
                animate={msg.animate}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <p className="px-5 text-[10px] text-gray-400 leading-relaxed" style={{ paddingTop: "6px" }}>
        输出内容仅供参考，不构成法律意见。重大法律事项请咨询专业律师。
      </p>

      {/* Input */}
      <div className="shrink-0 px-4 py-3" style={{ borderTop: "1px solid #f0f0f0" }}>
        <div
          className="flex gap-2 items-end rounded-2xl px-3 py-2 transition-all"
          style={{ border: "1.5px solid #e2e8f0", background: "#f8fafc" }}
          onFocusCapture={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "#3b82f6"; (e.currentTarget as HTMLDivElement).style.boxShadow = "0 0 0 3px rgba(59,130,246,0.1)"; }}
          onBlurCapture={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "#e2e8f0"; (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}
        >
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="输入劳动法问题… Enter 发送"
            rows={1}
            className="flex-1 bg-transparent text-sm text-gray-800 placeholder-gray-400 resize-none outline-none py-1 disabled:opacity-50 leading-relaxed"
          />
          <button
            onClick={onSubmit}
            disabled={isLoading || !inputValue.trim()}
            className="shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-white transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed mb-0.5"
            style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
          >
            {isLoading ? (
              <span className="flex gap-0.5">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1 h-1 rounded-full bg-white animate-bounce"
                    style={{ animationDelay: `${i * 0.12}s`, animationDuration: "0.7s" }}
                  />
                ))}
              </span>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
