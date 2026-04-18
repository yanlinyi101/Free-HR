"use client";

import { useEffect, useState, useMemo } from "react";
import { getApiBase } from "@/lib/settings";

interface LawMeta {
  law_name: string;
  region: string;
  article_count: number;
  effective_date: string | null;
}

const REGION_LABELS: Record<string, string> = {
  national: "国家",
  beijing: "北京",
  shanghai: "上海",
  guangdong: "广东",
};

export default function LawBrowser() {
  const [laws, setLaws] = useState<LawMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    setLoading(true);
    fetch(`${getApiBase()}/api/knowledge/laws`)
      .then((r) => {
        if (!r.ok) throw new Error("failed");
        return r.json() as Promise<{ laws: LawMeta[] }>;
      })
      .then((d) => { setLaws(d.laws); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return laws;
    const q = query.toLowerCase();
    return laws.filter((l) => l.law_name.includes(q) || (REGION_LABELS[l.region] ?? l.region).includes(q));
  }, [laws, query]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-gray-100">
        <h2 className="text-base font-semibold text-gray-900 mb-3">法条库</h2>
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索法律名称或地区…"
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-gray-50"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-gray-100 animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-sm">无法加载法条库</p>
            <p className="text-xs mt-1 text-gray-400">请确认后端服务正在运行</p>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-sm">{laws.length === 0 ? "暂无已入库法条" : "未找到匹配结果"}</p>
            {laws.length === 0 && (
              <p className="text-xs mt-2 text-gray-400 max-w-xs mx-auto">
                请运行 <code className="bg-gray-100 px-1 rounded text-gray-600">free-hr-ingest all</code> 灌入种子法条
              </p>
            )}
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-gray-400 mb-3">共 {filtered.length} 部法律</p>
            {filtered.map((law) => (
              <div
                key={`${law.law_name}-${law.region}`}
                className="flex items-center justify-between p-4 rounded-xl border border-gray-100 bg-white hover:border-blue-200 hover:shadow-sm transition-all cursor-default"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{law.law_name}</p>
                  {law.effective_date && (
                    <p className="text-xs text-gray-400 mt-0.5">施行：{law.effective_date}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-3 shrink-0">
                  <span className="text-xs text-gray-500">{law.article_count} 条</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
                    {REGION_LABELS[law.region] ?? law.region}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
