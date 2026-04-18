"use client";

import { useEffect, useState } from "react";
import { getChunk, Chunk } from "@/lib/api";

interface CitationDrawerProps {
  chunkId: string;
  onClose: () => void;
}

export default function CitationDrawer({ chunkId, onClose }: CitationDrawerProps) {
  const [chunk, setChunk] = useState<Chunk | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [visible, setVisible] = useState(false);

  // Animate in
  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  // ESC to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Fetch chunk
  useEffect(() => {
    setLoading(true);
    setError(false);
    getChunk(chunkId)
      .then((data) => {
        setChunk(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [chunkId]);

  const kindLabel = chunk?.kind === "law" ? "法条" : "案例";
  const kindColor =
    chunk?.kind === "law"
      ? "bg-blue-100 text-blue-700"
      : "bg-amber-100 text-amber-700";

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className={`fixed top-0 right-0 h-full w-full sm:w-[420px] bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col transition-transform duration-300 ${
          visible ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <span className="text-sm font-semibold text-gray-700">法律引用详情</span>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors text-lg leading-none p-1"
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {loading && (
            <div className="space-y-3 animate-pulse">
              <div className="h-5 bg-gray-100 rounded w-3/4" />
              <div className="h-4 bg-gray-100 rounded w-1/4" />
              <div className="h-40 bg-gray-100 rounded" />
            </div>
          )}

          {error && (
            <p className="text-sm text-red-500">加载失败，请稍后重试。</p>
          )}

          {!loading && !error && chunk && (
            <div className="space-y-4">
              <div>
                <h2 className="text-base font-semibold text-gray-900 leading-snug">
                  {chunk.label}
                </h2>
                <span
                  className={`inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded ${kindColor}`}
                >
                  {kindLabel}
                </span>
              </div>

              <hr className="border-gray-100" />

              <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap font-serif">
                {chunk.text}
              </div>

              {chunk.source_url && (
                <a
                  href={chunk.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 underline underline-offset-2"
                >
                  查看原文 ↗
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
