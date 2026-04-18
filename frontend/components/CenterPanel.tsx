"use client";

import { NavSection } from "./Sidebar";
import { Message } from "./MessageList";
import LawBrowser from "./LawBrowser";

interface QuickCard {
  title: string;
  desc: string;
  badge?: string;
  onClick?: () => void;
  icon: React.ReactNode;
}

function IconDoc() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}
function IconUsers() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
function IconSearch() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
    </svg>
  );
}

interface CenterPanelProps {
  activeNav: NavSection;
  messages: Message[];
  onNavigateToLaws: () => void;
}

function Dashboard({ messages, onNavigateToLaws }: { messages: Message[]; onNavigateToLaws: () => void }) {
  const QUICK_CARDS: QuickCard[] = [
    {
      title: "劳动合同审查",
      desc: "上传合同文件，AI 识别风险条款",
      badge: "即将推出",
      icon: <IconDoc />,
    },
    {
      title: "员工花名册风险",
      desc: "上传花名册，批量检测用工风险",
      badge: "即将推出",
      icon: <IconUsers />,
    },
    {
      title: "法条速查",
      desc: "按关键词搜索已入库法律法规",
      icon: <IconSearch />,
      onClick: onNavigateToLaws,
    },
  ];

  // Get last 3 Q&A pairs from messages
  const qaPairs: { q: string; a: string }[] = [];
  for (let i = 0; i < messages.length - 1; i++) {
    if (messages[i].role === "user" && messages[i + 1].role === "assistant") {
      qaPairs.push({ q: messages[i].text, a: messages[i + 1].text });
    }
  }
  const recentQA = qaPairs.slice(-3).reverse();

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-6 pt-7 pb-6 max-w-2xl">
        {/* Welcome */}
        <div
          className="rounded-2xl p-5 mb-6"
          style={{
            background: "linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%)",
            border: "1px solid #dbeafe",
          }}
        >
          <div className="flex items-start gap-4">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-base shrink-0"
              style={{ background: "linear-gradient(135deg, #2563eb, #1d4ed8)" }}
            >
              F
            </div>
            <div>
              <h1 className="text-base font-semibold text-gray-900">你好，欢迎使用 Free-HR</h1>
              <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                向右侧 AI 提问劳动法律问题，或选择下方功能模块开始工作。
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mb-7">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">功能模块</h2>
          <div className="grid grid-cols-1 gap-3">
            {QUICK_CARDS.map((card) => {
              const isClickable = !!card.onClick && !card.badge;
              return (
                <div
                  key={card.title}
                  onClick={card.onClick}
                  className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-150 ${
                    isClickable
                      ? "border-gray-200 bg-white cursor-pointer hover:border-blue-300 hover:shadow-md hover:-translate-y-0.5"
                      : "border-gray-100 bg-gray-50 cursor-default opacity-75"
                  }`}
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                    style={{
                      background: isClickable ? "#eff6ff" : "#f3f4f6",
                      color: isClickable ? "#2563eb" : "#9ca3af",
                    }}
                  >
                    {card.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-800">{card.title}</p>
                      {card.badge && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-500 font-medium leading-none">
                          {card.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{card.desc}</p>
                  </div>
                  {isClickable && (
                    <svg className="text-gray-300 mt-1 shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 18l6-6-6-6" />
                    </svg>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent chats */}
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">最近咨询</h2>
          {recentQA.length === 0 ? (
            <div className="text-center py-8 rounded-xl border border-dashed border-gray-200">
              <p className="text-sm text-gray-400">暂无咨询记录</p>
              <p className="text-xs text-gray-300 mt-1">向右侧 AI 对话框提问后，记录将显示在这里</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentQA.map((item, i) => (
                <div key={i} className="p-4 rounded-xl border border-gray-100 bg-white">
                  <p className="text-xs font-medium text-blue-600 mb-1 truncate">Q: {item.q}</p>
                  <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{item.a.replace(/\[#\d+\]/g, "")}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RiskPlaceholder() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-xs px-6">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 flex items-center justify-center mx-auto mb-4">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-gray-800 mb-1">风险预警</h3>
        <p className="text-xs text-gray-400 leading-relaxed">
          员工全周期风险看板，覆盖入职 → 在职 → 离职全流程，即将推出。
        </p>
        <span className="inline-block mt-3 text-[10px] px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 border border-amber-200 font-medium">
          Phase 3 计划中
        </span>
      </div>
    </div>
  );
}

export default function CenterPanel({ activeNav, messages, onNavigateToLaws }: CenterPanelProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden border-r border-gray-100" style={{ background: "#f8f9fa" }}>
      {/* Top bar */}
      <div
        className="shrink-0 px-6 py-3.5 flex items-center justify-between"
        style={{ background: "#fff", borderBottom: "1px solid #f0f0f0" }}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-1.5 h-4 rounded-full"
            style={{ background: "linear-gradient(to bottom, #2563eb, #1d4ed8)" }}
          />
          <span className="text-sm font-semibold text-gray-800">
            {activeNav === "dashboard" && "工作台"}
            {activeNav === "chat" && "AI 咨询"}
            {activeNav === "laws" && "法条库"}
            {activeNav === "risk" && "风险预警"}
          </span>
        </div>
        <span className="text-[10px] text-gray-400 font-medium">
          {new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "short" })}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeNav === "dashboard" && <Dashboard messages={messages} onNavigateToLaws={onNavigateToLaws} />}
        {activeNav === "chat" && <Dashboard messages={messages} onNavigateToLaws={onNavigateToLaws} />}
        {activeNav === "laws" && <LawBrowser />}
        {activeNav === "risk" && <RiskPlaceholder />}
      </div>
    </div>
  );
}
