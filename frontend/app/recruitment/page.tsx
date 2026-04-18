"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  createRequest,
  listRequests,
  RequestListItem,
  Status,
} from "@/lib/recruitment";

const STATUS_LABEL: Record<Status, string> = {
  drafting: "对话中",
  pending_review: "待审核",
  approved: "已通过",
};

const STATUS_COLOR: Record<Status, string> = {
  drafting: "bg-gray-200 text-gray-800",
  pending_review: "bg-orange-200 text-orange-900",
  approved: "bg-green-200 text-green-900",
};

export default function RecruitmentListPage() {
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    listRequests()
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function onCreate() {
    try {
      const req = await createRequest();
      router.push(`/recruitment/${req.id}`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-8 bg-white min-h-screen">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold">招聘需求</h1>
        <button
          onClick={onCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          ＋ 新建招聘需求
        </button>
      </div>
      {error && <div className="text-red-600 mb-4">加载失败：{error}</div>}
      {loading ? (
        <div>加载中…</div>
      ) : items.length === 0 ? (
        <div className="text-gray-500">还没有招聘需求，点右上角新建一条。</div>
      ) : (
        <ul className="divide-y border rounded">
          {items.map((it) => (
            <li key={it.id}>
              <Link
                href={`/recruitment/${it.id}`}
                className="flex justify-between items-center p-4 hover:bg-gray-50"
              >
                <div>
                  <div className="font-medium">{it.title}</div>
                  <div className="text-sm text-gray-500">
                    更新于 {new Date(it.updated_at).toLocaleString()}
                  </div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded ${STATUS_COLOR[it.status]}`}
                >
                  {STATUS_LABEL[it.status]}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
