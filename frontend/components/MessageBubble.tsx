"use client";

import { useEffect, useState } from "react";
import { Citation } from "@/lib/api";
import { useTypewriter } from "@/lib/typewriter";
import CitationBadge from "./CitationBadge";

interface MessageBubbleProps {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  isLoading?: boolean;
  onCitationClick?: (chunkId: string) => void;
  animate?: boolean;
}

type Fragment = string | { idx: number };

function parseFragments(text: string): Fragment[] {
  const parts: Fragment[] = [];
  const regex = /\[#(\d+)\]/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    parts.push({ idx: parseInt(match[1], 10) });
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return parts;
}

function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s`, animationDuration: "0.8s" }}
        />
      ))}
    </span>
  );
}

export default function MessageBubble({
  role,
  text,
  citations = [],
  isLoading = false,
  onCitationClick,
  animate = false,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const [ready, setReady] = useState(!animate);

  // Always call useTypewriter — conditionally apply its output
  const typewriterText = useTypewriter(animate ? text : "");
  const displayText = animate && !ready ? typewriterText : text;

  // Once typewriter text reaches full length, mark as ready
  useEffect(() => {
    if (animate && typewriterText === text && text.length > 0) {
      setReady(true);
    }
  }, [animate, typewriterText, text]);

  const fragments = parseFragments(displayText);

  const handleCitationClick = (idx: number) => {
    const citation = citations.find((c) => c.idx === idx);
    if (citation && onCitationClick) {
      onCitationClick(citation.chunk_id);
    }
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0">
          F
        </div>
      )}
      <div
        className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-blue-700 text-white rounded-tr-sm"
            : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"
        }`}
      >
        {isLoading ? (
          <LoadingDots />
        ) : (
          <span>
            {fragments.map((fragment, i) => {
              if (typeof fragment === "string") {
                return <span key={i}>{fragment}</span>;
              }
              return (
                <CitationBadge
                  key={i}
                  idx={fragment.idx}
                  onClick={handleCitationClick}
                />
              );
            })}
          </span>
        )}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-xs font-bold ml-2 mt-1 shrink-0">
          您
        </div>
      )}
    </div>
  );
}
