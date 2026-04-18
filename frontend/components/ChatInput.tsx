"use client";

import { useRef, useEffect } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  return (
    <div className="px-4 py-3 bg-white border-t border-gray-100">
      <div className="max-w-[760px] mx-auto flex gap-2 items-end">
        <div className="flex-1 border border-gray-200 rounded-2xl bg-gray-50 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="输入您的劳动法问题… (Enter 发送，Shift+Enter 换行)"
            rows={1}
            className="w-full px-4 py-3 bg-transparent text-sm text-gray-800 placeholder-gray-400 resize-none outline-none rounded-2xl disabled:opacity-50"
          />
        </div>
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          className="shrink-0 px-4 py-3 rounded-2xl bg-blue-700 text-white text-sm font-medium hover:bg-blue-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          发送
        </button>
      </div>
    </div>
  );
}
