"use client";

import { useState, useCallback } from "react";
import { postChat, Citation } from "@/lib/api";
import MessageList, { Message } from "@/components/MessageList";
import ChatInput from "@/components/ChatInput";
import EmptyState from "@/components/EmptyState";
import Disclaimer from "@/components/Disclaimer";
import CitationDrawer from "@/components/CitationDrawer";
import SettingsModal from "@/components/SettingsModal";

let msgCounter = 0;
function nextId() {
  return String(++msgCounter);
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [drawerChunkId, setDrawerChunkId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isLoading) return;

      const userMsg: Message = {
        id: nextId(),
        role: "user",
        text: trimmed,
      };

      const loadingId = nextId();
      const loadingMsg: Message = {
        id: loadingId,
        role: "assistant",
        text: "",
        isLoading: true,
      };

      setMessages((prev) => [...prev, userMsg, loadingMsg]);
      setInputValue("");
      setIsLoading(true);

      try {
        const response = await postChat(trimmed);
        const assistantMsg: Message = {
          id: nextId(),
          role: "assistant",
          text: response.text,
          citations: response.citations,
          animate: true,
        };

        setMessages((prev) => {
          const withoutLoading = prev.filter((m) => m.id !== loadingId);
          return [...withoutLoading, assistantMsg];
        });
      } catch {
        const errorMsg: Message = {
          id: nextId(),
          role: "assistant",
          text: "请求失败，请稍后重试。",
        };
        setMessages((prev) => {
          const withoutLoading = prev.filter((m) => m.id !== loadingId);
          return [...withoutLoading, errorMsg];
        });
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading]
  );

  const handleSubmit = () => sendMessage(inputValue);

  const handlePromptClick = (prompt: string) => {
    setInputValue(prompt);
    sendMessage(prompt);
  };

  const handleCitationClick = useCallback((chunkId: string) => {
    setDrawerChunkId(chunkId);
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerChunkId(null);
  }, []);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="shrink-0 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
        <div className="max-w-[760px] mx-auto px-4 py-3 flex items-center justify-between">
          <span className="font-semibold text-gray-900 text-base">
            Free-HR 法律咨询
          </span>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 font-medium border border-gray-200">
              MVP · 北京
            </span>
            <button
              onClick={() => setShowSettings(true)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              title="API 设置"
              aria-label="API 设置"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      {isEmpty ? (
        <EmptyState onPromptClick={handlePromptClick} />
      ) : (
        <MessageList messages={messages} onCitationClick={handleCitationClick} />
      )}

      {/* Disclaimer */}
      <Disclaimer />

      {/* Input */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSubmit}
        disabled={isLoading}
      />

      {/* Citation drawer */}
      {drawerChunkId && (
        <CitationDrawer chunkId={drawerChunkId} onClose={closeDrawer} />
      )}

      {/* Settings modal */}
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
}
