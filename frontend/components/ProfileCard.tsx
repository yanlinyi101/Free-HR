"use client";

import { Profile } from "@/lib/recruitment";

type FieldRow = { label: string; value: string | null };

function group(title: string, rows: FieldRow[]) {
  return (
    <div className="mb-4">
      <div className="text-xs font-semibold text-gray-500 mb-1">{title}</div>
      <div className="space-y-1 text-sm">
        {rows.map((r) => (
          <div key={r.label} className="flex">
            <div className="w-24 text-gray-500">{r.label}</div>
            <div className={r.value ? "text-gray-900" : "text-gray-400 italic"}>
              {r.value ?? "待补充"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function listOrPlaceholder(list: string[]): string | null {
  return list.length > 0 ? list.join("、") : null;
}

export function ProfileCard({ profile }: { profile: Profile }) {
  return (
    <div className="p-4 border-b">
      <h3 className="font-semibold mb-3">候选人画像</h3>
      {group("岗位基础", [
        { label: "职位名称", value: profile.position.title },
        { label: "所属部门", value: profile.position.department },
        { label: "汇报对象", value: profile.position.report_to },
        { label: "编制", value: profile.position.headcount?.toString() ?? null },
        { label: "工作地点", value: profile.position.location },
        { label: "到岗时间", value: profile.position.start_date },
      ])}
      {group("岗位职责", [
        { label: "核心职责", value: listOrPlaceholder(profile.responsibilities) },
      ])}
      {group("硬性要求", [
        { label: "学历", value: profile.hard_requirements.education },
        { label: "工作年限", value: profile.hard_requirements.years },
        { label: "必备技能", value: listOrPlaceholder(profile.hard_requirements.skills) },
        { label: "行业背景", value: profile.hard_requirements.industry },
      ])}
      {group("软性偏好", [
        { label: "加分项", value: listOrPlaceholder(profile.soft_preferences.bonus_points) },
        { label: "文化匹配", value: profile.soft_preferences.culture_fit },
        { label: "团队风格", value: profile.soft_preferences.team_style },
      ])}
      {group("薪资与汇报", [
        { label: "薪资范围", value: profile.compensation.salary_range },
        { label: "级别", value: profile.compensation.level },
        { label: "雇佣形式", value: profile.compensation.employment_type },
      ])}
    </div>
  );
}
