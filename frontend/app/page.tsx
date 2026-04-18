"use client";

import { useState, useCallback } from "react";
import { postChat, Citation } from "@/lib/api";
import { Message } from "@/components/MessageList";
import Sidebar, { NavSection } from "@/components/Sidebar";
import CenterPanel from "@/components/CenterPanel";
import ChatPanel from "@/components/ChatPanel";
import CitationDrawer from "@/components/CitationDrawer";
import SettingsModal from "@/components/SettingsModal";

let msgCounter = 0;
const nextId = () => String(++msgCounter);

export default function AppPage() {
  const [activeNav, setActiveNav] = useState<NavSection>("dashboard");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [drawerChunkId, setDrawerChunkId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isLoading) return;

      const userMsg: Message = { id: nextId(), role: "user", text: trimmed };
      const loadingId = nextId();
      const loadingMsg: Message = { id: loadingId, role: "assistant", text: "", isLoading: true };

      setMessages((prev) => [...prev, userMsg, loadingMsg]);
      setInputValue("");
      setIsLoading(true);
      // Switch to chat nav to highlight it
      setActiveNav("chat");

      try {
        const response = await postChat(trimmed);
        const assistantMsg: Message = {
          id: nextId(),
          role: "assistant",
          text: response.text,
          citations: response.citations as Citation[],
          animate: true,
        };
        setMessages((prev) => [...prev.filter((m) => m.id !== loadingId), assistantMsg]);
      } catch {
        const errorMsg: Message = {
          id: nextId(),
          role: "assistant",
          text: "请求失败，请检查后端服务是否正常运行。",
        };
        setMessages((prev) => [...prev.filter((m) => m.id !== loadingId), errorMsg]);
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

  return (
    <>
      {/* Three-column layout: 1/5 | 2/5 | 2/5 */}
      <div
        className="h-screen overflow-hidden"
        style={{ display: "grid", gridTemplateColumns: "1fr 2fr 2fr" }}
      >
        <Sidebar
          active={activeNav}
          onNavigate={setActiveNav}
          onOpenSettings={() => setShowSettings(true)}
        />

        <CenterPanel
          activeNav={activeNav}
          messages={messages}
          onNavigateToLaws={() => setActiveNav("laws")}
        />

        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          isLoading={isLoading}
          onCitationClick={setDrawerChunkId}
          onPromptClick={handlePromptClick}
        />
      </div>

      {/* Mobile: show only chat panel below 768px */}
      <style>{`
        @media (max-width: 767px) {
          [data-three-col] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>

      {drawerChunkId && (
        <CitationDrawer chunkId={drawerChunkId} onClose={() => setDrawerChunkId(null)} />
      )}
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}
