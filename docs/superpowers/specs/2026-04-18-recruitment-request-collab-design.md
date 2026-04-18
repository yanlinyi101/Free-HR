# 招聘需求协作模块 设计文档

> 日期：2026-04-18
> 状态：Design (approved, pending implementation plan)
> 所属：Free-HR / 新模块 `recruitment`

## 1. 背景与目标

Free-HR 现有 MVP 聚焦 HR 用工合规问答（`POST /api/chat`）。本设计新增一个**招聘需求协作**模块，支持：

- 业务部门（用人经理）自助发起招聘需求
- AI 通过多轮对话引导 + 自由描述 + 字段抽取，逐步形成候选人画像
- 画像必填项齐备后，一次性生成 JD（Markdown）
- HR 审核：编辑 JD，点"通过"定稿

本模块是 Free-HR 的**新模块**（非独立产品），复用账号（未来）、LLM 客户端、DB、对话 UI 骨架，但数据与 API 独立。

## 2. 范围（MVP）

### 包含

- 需求单 CRUD（创建 / 列表 / 详情 / 审核通过）
- 对话驱动的字段抽取（AI 引导 + 用户自由描述，抽取后追问缺项）
- 画像字段卡片实时刷新
- JD 一次性生成（字段抽满后）
- HR 编辑 JD + 两态审核（`pending_review` → `approved`）

### 不包含（显式 YAGNI）

- 账号 / 权限 / 角色分离（沿用当前匿名模式）
- 通知 / @提醒 / 评论
- 岗位模板库、历史 JD 复用
- HR 打回重新对话（两态审核的刻意简化）
- SSE 流式响应
- 对话摘要 / 压缩（硬限制 20 轮以内）

## 3. 用户角色与流程

MVP 不做角色分离，所有请求匿名。语义上两类使用者：

- **业务（用人经理）**：发起需求单，与 AI 对话细化画像，点"生成 JD"
- **HR**：在列表看到 `pending_review` 的需求单，编辑 JD 文本，点"通过"

### 核心流程

```
业务：创建需求单 → 多轮对话（AI 追问缺项）→ 必填齐 → 生成 JD → status = pending_review
HR：  列表筛 pending_review → 详情页编辑 JD → 点"通过"→ status = approved
```

## 4. 架构与模块边界

### 后端新增（`backend/free_hr/`）

| 文件 | 职责 |
|---|---|
| `recruitment/models.py` | SQLAlchemy 模型：`RecruitmentRequest` / `RequestMessage` / `JDDraft` |
| `recruitment/service.py` | 对话编排：缺项判定、助手回复生成、状态机转换 |
| `recruitment/extractor.py` | LLM 结构化字段抽取（对话历史 → `profile` JSON） |
| `recruitment/jd_generator.py` | 完整 `profile` → Markdown JD |
| `api/recruitment.py` | FastAPI 路由 |

### 前端新增（`frontend/`）

- 顶部导航新增「招聘协作」入口（与「法律问答」并列）
- `/recruitment` 列表页
- `/recruitment/[id]` 详情页（对话 + 字段卡片 + JD 预览）

### 复用与不复用

- **复用**：LLM 客户端、DB session、配置、chat 消息气泡样式
- **不复用** `/api/chat`（保留纯 RAG 单轮语义），新增独立 endpoints

## 5. 数据模型

### `recruitment_request`

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | UUID PK | |
| `title` | varchar | 岗位名称（抽到后回填；占位 `"新需求-{timestamp}"`） |
| `status` | enum | `drafting` / `pending_review` / `approved` |
| `profile` | jsonb | 见下 |
| `created_at` / `updated_at` | timestamptz | |

未来账号接入时新增 `created_by` / `reviewed_by`。

### `profile` JSON 结构

```json
{
  "position": {
    "title": null,
    "department": null,
    "report_to": null,
    "headcount": null,
    "location": null,
    "start_date": null
  },
  "responsibilities": [],
  "hard_requirements": {
    "education": null,
    "years": null,
    "skills": [],
    "industry": null
  },
  "soft_preferences": {
    "bonus_points": [],
    "culture_fit": null,
    "team_style": null
  },
  "compensation": {
    "salary_range": null,
    "level": null,
    "employment_type": null
  }
}
```

**必填字段**（决定 `ready_for_jd`）：

- `position.title`
- `position.department`
- `responsibilities`（非空列表）
- `hard_requirements.skills`（非空列表）
- `compensation.salary_range`

### `request_message`

| 列 | 类型 |
|---|---|
| `id` | UUID PK |
| `request_id` | UUID FK → `recruitment_request.id` |
| `role` | enum `user` / `assistant` |
| `content` | text |
| `created_at` | timestamptz |

不存 RAG 引用（招聘对话不触发法律 RAG）。

### `jd_draft`

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | UUID PK | |
| `request_id` | UUID FK | 1:1 |
| `content_md` | text | AI 生成的原版 JD |
| `edited_content_md` | text nullable | HR 编辑后版本，空则 = 原版 |
| `generated_at` | timestamptz | |
| `approved_at` | timestamptz nullable | |

### 状态机

```
drafting ──[字段抽满 + 用户点"生成 JD"]──> pending_review
pending_review ──[HR 点"通过"]──> approved
pending_review ──[HR 编辑 JD]──> pending_review  (内容变，状态不变)
```

MVP 不支持：`approved → *`、`pending_review → drafting`（打回）。

## 6. API 设计

所有路径前缀 `/api/recruitment`。

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/requests` | 创建空需求单，返回 `{id, status: "drafting", profile, title}` |
| `GET` | `/requests` | 列表：`[{id, title, status, updated_at}]`，按 `updated_at desc` |
| `GET` | `/requests/{id}` | 详情：需求单 + 对话历史 + JD 草稿（若有） |
| `POST` | `/requests/{id}/messages` | 追加用户消息 → 抽取 → 生成回复。返回 `{assistant_message, profile, missing_fields, ready_for_jd}` |
| `POST` | `/requests/{id}/jd` | 前置 `ready_for_jd=true`；生成 JD，状态转 `pending_review` |
| `PATCH` | `/requests/{id}` | HR 操作：body 可包含 `edited_content_md`（编辑 JD）和/或 `action: "approve"`（通过） |

### 非法状态转换响应

- `POST /requests/{id}/jd` 当 `ready_for_jd=false` → `400 { "error": "missing_fields", "fields": [...] }`
- `PATCH {action: "approve"}` 当 `status != pending_review` → `409 { "error": "invalid_state" }`

## 7. 对话编排与字段抽取

### 单轮处理流程（`POST /requests/{id}/messages`）

1. 追加 user 消息到 `request_message`
2. **抽取**（`extractor.py`）：输入 = 当前 `profile` + 完整对话历史；输出 = 更新后的 `profile`；LLM 结构化输出（JSON schema 约束），低温度
3. **合并**：新抽出的非空字段覆盖旧字段；**已填字段不被 null 覆盖**（防止 LLM 漏抽导致字段回退）
4. **缺项判定**：扫 `profile`，列出所有 null / 空列表字段
5. **生成助手回复**（`service.py`）：Prompt 含
   - 已知字段摘要
   - 缺项列表（按优先级排序）
   - 策略：自然追问 1–2 个相关缺项，不做表单式盘问；若用户自由描述含多字段，先确认再追问剩余
6. 持久化 assistant 消息，返回 `{assistant_message, profile, missing_fields, ready_for_jd}`

### 两次 LLM 调用的决策

抽取和回复生成**分两次调用**：

- 抽取：严格 JSON schema + 低温度 + "只抽明确提到的信息，不要推断"
- 回复：自然对话风格，较高温度

合并成一次调用会让任一方退化（结构化变松 / 自然度变差）。

### 对话历史策略

MVP 每次**全量传**完整对话历史。软硬限制：

- 软限：前端在 15 轮时提示"继续对话将较长"
- 硬限：20 轮后 `POST /messages` 返回 `409 { "error": "conversation_too_long" }`，建议先生成 JD

### JD 生成（`POST /requests/{id}/jd`）

- 前置：`ready_for_jd=true`
- `jd_generator.py`：Prompt = 完整 `profile`；输出固定段落 Markdown：
  1. 职位标题
  2. 岗位职责
  3. 任职要求
  4. 薪资福利
  5. 工作地点与汇报
- 写入 `jd_draft`，状态转 `pending_review`

## 8. 前端交互

### `/recruitment`（列表页）

- 顶部"＋ 新建招聘需求"按钮 → `POST /requests` → 跳详情
- 列表项：标题、状态 badge（drafting=灰 / pending_review=橙 / approved=绿）、更新时间
- MVP 不做角色过滤

### `/recruitment/[id]`（详情页）

布局：左 60% 对话 / 右 40% 画像+JD。

**左栏（对话）**

- 消息气泡复用现有 chat 样式
- 底部输入框 + 发送
- "生成 JD"按钮常驻；`ready_for_jd=false` 时禁用并显示 tooltip："还需补充：{缺项列表}"

**右栏**

- **上半 画像字段卡片**：按 5 组展示，已填字段正常，null/空列表灰色占位"待补充"。每次 `POST /messages` 响应后刷新
- **下半 JD 预览**：
  - 生成前：占位文案"完成对话后生成 JD"
  - 生成后：Markdown 渲染
  - HR 视角："编辑"按钮进 textarea → 保存调 `PATCH {edited_content_md}`；"通过"按钮调 `PATCH {action: "approve"}`

## 9. 错误处理

| 场景 | 处理 |
|---|---|
| 抽取 LLM 调用失败 | 不阻塞对话：保留旧 profile，仍生成助手回复，前端提示"字段未更新" |
| 抽取返回非法 JSON | 重试 1 次；仍失败回退为"不更新 profile"（同上） |
| 回复生成 LLM 失败 | `POST /messages` 返回 `503`；前端气泡显示错误 + 重试按钮；user 消息已落库不丢 |
| JD 生成失败 | `POST /jd` 返回 `503`；状态保持 `drafting`；前端 toast + 重试 |
| 非法状态转换 | `400` / `409`（见 API 节） |
| 并发编辑同一需求单 | 不加锁；乐观更新，后写覆盖（MVP 单人用够） |

## 10. 测试计划

### 单元测试（`backend/tests/unit/`）

- `test_extractor.py`：mock LLM，验证
  - 字段合并（新值覆盖旧值）
  - 已填字段不被 null 覆盖
  - JSON 解析失败回退路径
  - 必填判定逻辑（`ready_for_jd`）
- `test_service.py`：
  - 缺项列表生成与优先级排序
  - 状态机合法/非法转换（`drafting → pending_review → approved` OK；其他 raise）
- `test_jd_generator.py`：mock LLM，验证 prompt 包含全部 profile 字段；返回 Markdown 字符串

### 集成测试（`backend/tests/integration/test_recruitment_api.py`）

用 FastAPI `TestClient` + mock LLM，走完整链路：

1. `POST /requests` → 得到 id
2. 多轮 `POST /messages` 逐步填充 profile（断言 `ready_for_jd` 翻转）
3. `POST /jd` 成功，状态 = `pending_review`
4. `PATCH /{id} {edited_content_md}` 成功，内容落库
5. `PATCH /{id} {action: "approve"}` 成功，状态 = `approved`
6. 反例：未满足 `ready_for_jd` 调 `/jd` → 400；`approved` 后再 approve → 409

## 11. 数据库迁移

新增 Alembic revision：

- 创建 3 张表与索引（`recruitment_request(status)`、`request_message(request_id, created_at)`）
- 无现有数据影响（纯新增）

## 12. 后续可扩展点（非 MVP）

- 账号接入后：`created_by` / `reviewed_by` / 列表按角色过滤 / 通知
- HR 打回：新增 `needs_revision` 状态 + 打回评论
- 岗位模板库：预填 `profile`
- 历史 JD 复用：按岗位相似度推荐
- SSE 流式回复
- 对话摘要压缩，突破 20 轮硬限
