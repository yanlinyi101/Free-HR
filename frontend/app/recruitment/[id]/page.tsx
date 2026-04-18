"use client";

import { useEffect, useState, use } from "react";
import { getRequest, RequestRead } from "@/lib/recruitment";
import { ProfileCard } from "@/components/ProfileCard";
import { JDPanel } from "@/components/JDPanel";
import { RecruitmentChat } from "@/components/RecruitmentChat";

export default function RecruitmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [req, setReq] = useState<RequestRead | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRequest(id).then(setReq).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!req) return <main className="p-8">加载中…</main>;

  return (
    <main className="h-screen flex flex-col">
      <header className="border-b px-6 py-3 flex items-center justify-between">
        <div>
          <a href="/recruitment" className="text-sm text-blue-600">← 返回列表</a>
          <h1 className="text-lg font-semibold">{req.title}</h1>
        </div>
        <span className="text-xs px-2 py-1 rounded bg-gray-200">{req.status}</span>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-3/5 border-r">
          <RecruitmentChat request={req} onUpdated={setReq} />
        </div>
        <div className="w-2/5 overflow-y-auto">
          <ProfileCard profile={req.profile} />
          <JDPanel request={req} onUpdated={setReq} />
        </div>
      </div>
    </main>
  );
}
