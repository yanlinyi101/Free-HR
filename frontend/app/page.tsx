"use client";

import { useState, useCallback } from "react";
import { postChat, Citation } from "@/lib/api";
import MessageList, { Message } from "@/components/MessageList";
import ChatInput from "@/components/ChatInput";
import EmptyState from "@/components/EmptyState";
import Disclaimer from "@/components/Disclaimer";
import CitationDrawer from "@/components/CitationDrawer";

let msgCounter = 0;
function nextId() {
  return String(++msgCounter);
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [drawerChunkId, setDrawerChunkId] = useState<string | null>(null);

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
          <span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 font-medium border border-gray-200">
            MVP · 北京
          </span>
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
    </div>
  );
}
