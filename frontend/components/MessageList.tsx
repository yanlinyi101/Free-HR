"use client";

import { useEffect, useRef } from "react";
import { Citation } from "@/lib/api";
import MessageBubble from "./MessageBubble";

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  isLoading?: boolean;
  animate?: boolean;
}

interface MessageListProps {
  messages: Message[];
  onCitationClick: (chunkId: string) => void;
}

export default function MessageList({ messages, onCitationClick }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-[760px] mx-auto">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            text={msg.text}
            citations={msg.citations}
            isLoading={msg.isLoading}
            onCitationClick={onCitationClick}
            animate={msg.animate}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
