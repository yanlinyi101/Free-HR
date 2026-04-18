"use client";

const SAMPLE_PROMPTS = [
  "员工严重违反规章制度可以直接解除吗？",
  "试用期可以不签劳动合同吗？",
  "经济补偿金如何计算？",
];

interface EmptyStateProps {
  onPromptClick: (prompt: string) => void;
}

export default function EmptyState({ onPromptClick }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-4 py-16 text-center">
      <div className="mb-3">
        <span className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-700 text-white text-2xl font-bold shadow-lg">
          F
        </span>
      </div>
      <h1 className="text-xl font-semibold text-gray-900 mb-2 leading-snug">
        向 Free-HR 提问中国大陆劳动法相关问题
      </h1>
      <p className="text-sm text-gray-500 mb-8 max-w-sm">
        基于中国劳动法、劳动合同法等法规，为您提供专业参考。
      </p>

      <div className="flex flex-col sm:flex-row gap-2 flex-wrap justify-center max-w-xl">
        {SAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onPromptClick(prompt)}
            className="px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-gray-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition-colors text-left shadow-sm"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
