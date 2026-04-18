"use client";

interface CitationBadgeProps {
  idx: number;
  onClick: (idx: number) => void;
}

export default function CitationBadge({ idx, onClick }: CitationBadgeProps) {
  return (
    <button
      onClick={() => onClick(idx)}
      className="inline-flex items-center mx-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 cursor-pointer hover:bg-blue-100 hover:border-blue-300 transition-colors leading-none align-baseline"
      title={`查看引用 #${idx}`}
    >
      #{idx}
    </button>
  );
}
