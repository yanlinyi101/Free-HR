"use client";

import { useState } from "react";
import { JDRead, patchRequest, RequestRead, Status } from "@/lib/recruitment";

export function JDPanel({
  request,
  onUpdated,
}: {
  request: RequestRead;
  onUpdated: (r: RequestRead) => void;
}) {
  const jd: JDRead | null = request.jd;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  if (jd === null) {
    return (
      <div className="p-4 text-gray-400 italic">
        完成对话后生成 JD
      </div>
    );
  }

  const current = jd.edited_content_md ?? jd.content_md;
  const status: Status = request.status;

  async function onSaveEdit() {
    try {
      const r = await patchRequest(request.id, { edited_content_md: draft });
      onUpdated(r);
      setEditing(false);
    } catch (e) {
      setError(String(e));
    }
  }

  async function onApprove() {
    try {
      const r = await patchRequest(request.id, { action: "approve" });
      onUpdated(r);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">JD 草稿</h3>
        <div className="space-x-2">
          {!editing && status === "pending_review" && (
            <>
              <button
                onClick={() => {
                  setDraft(current);
                  setEditing(true);
                }}
                className="text-sm px-3 py-1 border rounded"
              >
                编辑
              </button>
              <button
                onClick={onApprove}
                className="text-sm px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
              >
                通过
              </button>
            </>
          )}
          {status === "approved" && (
            <span className="text-sm text-green-700">已通过</span>
          )}
        </div>
      </div>
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      {editing ? (
        <>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full h-96 border rounded p-2 font-mono text-sm"
          />
          <div className="mt-2 space-x-2">
            <button onClick={onSaveEdit} className="px-3 py-1 bg-blue-600 text-white rounded">
              保存
            </button>
            <button onClick={() => setEditing(false)} className="px-3 py-1 border rounded">
              取消
            </button>
          </div>
        </>
      ) : (
        <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-3 rounded border">{current}</pre>
      )}
    </div>
  );
}
