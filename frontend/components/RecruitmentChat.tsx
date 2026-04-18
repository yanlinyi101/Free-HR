"use client";

import { useState } from "react";
import { generateJD, MessageRead, postMessage, RequestRead } from "@/lib/recruitment";

export function RecruitmentChat({
  request,
  onUpdated,
}: {
  request: RequestRead;
  onUpdated: (r: RequestRead) => void;
}) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<MessageRead[]>(request.messages);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSend() {
    if (!input.trim() || sending) return;
    const content = input.trim();
    const userMsg: MessageRead = {
      id: `local-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((ms) => [...ms, userMsg]);
    setInput("");
    setSending(true);
    setError(null);
    try {
      const resp = await postMessage(request.id, content);
      setMessages((ms) => [...ms, resp.assistant_message]);
      onUpdated({
        ...request,
        profile: resp.profile,
        missing_fields: resp.missing_fields,
        ready_for_jd: resp.ready_for_jd,
        messages: [...request.messages, userMsg, resp.assistant_message],
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setSending(false);
    }
  }

  async function onGenerate() {
    setSending(true);
    setError(null);
    try {
      const r = await generateJD(request.id);
      onUpdated(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setSending(false);
    }
  }

  const canGenerate = request.ready_for_jd && request.status === "drafting";
  const generateTooltip = canGenerate
    ? ""
    : request.status !== "drafting"
    ? "已生成 JD"
    : `还需补充：${request.missing_fields.join("、")}`;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-gray-500 text-sm">
            你好，请描述你要招聘的岗位。例如&ldquo;我要招一个后端工程师，技术部，Python 方向，3-5 年经验，25-40k&rdquo;。
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`max-w-[80%] p-3 rounded ${
              m.role === "user" ? "bg-blue-100 ml-auto" : "bg-gray-100"
            }`}
          >
            <div className="whitespace-pre-wrap text-sm">{m.content}</div>
          </div>
        ))}
        {sending && <div className="text-gray-400 text-sm">生成中…</div>}
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </div>
      <div className="border-t p-3 space-y-2">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
            placeholder="描述你要招聘的岗位…（Enter 发送，Shift+Enter 换行）"
            className="flex-1 border rounded p-2 text-sm resize-none h-20"
            disabled={sending || request.status === "approved"}
          />
          <button
            onClick={onSend}
            disabled={sending || !input.trim() || request.status === "approved"}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-gray-400"
          >
            发送
          </button>
        </div>
        <button
          onClick={onGenerate}
          disabled={!canGenerate || sending}
          title={generateTooltip}
          className="w-full py-2 bg-green-600 text-white rounded disabled:bg-gray-300 disabled:text-gray-500"
        >
          生成 JD
          {!canGenerate && request.status === "drafting" && (
            <span className="ml-2 text-xs">（{generateTooltip}）</span>
          )}
        </button>
      </div>
    </div>
  );
}
