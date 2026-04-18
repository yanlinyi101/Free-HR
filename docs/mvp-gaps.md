# Phase 1 MVP 缺口清单

> 原始计划：16 个 Task，完整版 Phase 1。  
> MVP 实际交付：Task 1–4、6–10（部分简化）+ 前端（单页简化版）。  
> 本文件列出 MVP 与完整版计划之间的所有差距，供后续排期参考。

---

## 1. 鉴权模块（Task 5）— 完全未实现

**原计划内容：**
- `backend/src/free_hr/auth/` — security / repo / service / deps / schemas
- JWT 签发 & 校验（`python-jose`）、bcrypt 密码哈希（`passlib`）
- `POST /api/auth/login`、`POST /api/auth/register`（仅 admin 可调用）、`GET /api/auth/me`
- `current_user` FastAPI Dependency（Bearer Token → User ORM）
- `require_admin` Dependency（role 校验）
- `bootstrap_admin`：应用启动时自动创建初始管理员账号
- 单元测试：hash/verify/token roundtrip
- 集成测试：register → login → me 完整流程

**现状：**  
DB 里 `users` 表已建好，但无任何鉴权代码。所有 API 接口完全公开，任何人都能调用。

**实现工作量：** 约 4–6 h（代码已在计划文件中完整列出，可直接实现）。

---

## 2. 会话持久化（Task 9 + 10 简化）— 数据库在，业务层缺失

**原计划内容：**
- `backend/src/free_hr/chat/repo.py`：`create_session / list_sessions / get_session_for_user / list_messages / append_message`
- `stream_answer()` 异步生成器：将用户消息存入 DB，流式生成 LLM 回答，最终将 assistant 消息 + 引用写回 DB
- API 端点：`POST /api/chat/sessions`（建会话）、`GET /api/chat/sessions`（列会话）、`GET /api/chat/sessions/{id}/messages`（历史消息）

**现状：**  
MVP 使用 `answer_once()` 无状态函数，不写入 DB。`chat_sessions / chat_messages` 表已建好但完全未用。页面刷新后聊天记录全部丢失。

**实现工作量：** 约 3–4 h。

---

## 3. SSE 流式回答（Task 9 + 10 + 13 简化）— 体验降级

**原计划内容：**
- 后端：`stream_answer()` 以 `AsyncIterator[ChatEvent]` 形式逐 token yield
- API：`POST /api/chat/sessions/{id}/messages` 返回 `EventSourceResponse`（SSE）
- 前端：`lib/sse.ts` fetch-based SSE reader（支持 POST + Bearer Token）；消息气泡实时追加 token

**现状：**  
后端一次性返回完整 JSON，前端用打字机动画模拟流式效果。首 token 延迟 = 全量生成时间（长问题可达 10–30 秒空白等待）。

**实现工作量：** 约 4–5 h（后端 `stream_answer` 已有完整设计；前端需改 `api.ts` + `MessageBubble`）。

---

## 4. 前端完整版（Tasks 11–14 简化）— 多项功能缺失

| 功能 | 完整版计划 | MVP 现状 |
|------|-----------|---------|
| UI 组件库 | shadcn/ui（Button / Dialog / Sheet 等） | 纯 Tailwind 手写 |
| 登录页 | 独立 `/login` 路由，JWT 存 localStorage | 无，所有 API 匿名 |
| Auth Store | Zustand store，token 持久化，自动刷新 | 无 |
| 会话侧栏 | 左侧边栏列出所有会话，支持新建/切换 | 无，单次对话，刷新即清空 |
| 多会话上下文 | 历史消息随会话 ID 拉取，发送时携带历史 | 无 |
| SSE 实时流 | 真实 token 流，逐字追加 | 全量返回 + 打字机动画 |
| Sources 页 | 独立 `/sources` 路由，浏览全部已入库法条 | 无（引用抽屉已有，但无独立 Sources 页） |

**实现工作量：** 约 12–16 h。

---

## 5. 案例（case_chunks）入库流程 — 缺失

**原计划内容：**
- `knowledge_ingest/` 支持案例文件解析（格式与法条文件不同）
- CLI `all` 命令同时灌入法条 + 案例

**现状：**  
`case_chunks` 表已建好，`search_cases()` 也已实现，但没有任何案例入库工具。RAG 检索时 `case_hits` 永远为空，引用来源全部是法条。

**实现工作量：** 约 2–3 h（定义案例文件格式 → `chunk_case()` → `ingest_case_file()` → CLI 命令）。

---

## 6. 集成测试（依赖真实 Postgres）— 全部跳过

以下测试文件已创建但未执行（无本地 Postgres / Docker）：

- `tests/integration/test_knowledge_schema.py` — DDL 验证
- `tests/integration/test_knowledge_store.py` — pgvector 相似度搜索
- `tests/integration/test_ingest_pipeline.py` — 端到端入库
- `tests/integration/test_chat_flow.py`（原计划版本）— RAG 流程 + DB 写入

**影响：** 这些路径未经真实 DB 验证。migration、pgvector HNSW 索引、CAST 语法只经过代码审查，未实际运行。

---

## 7. Docker Compose + 种子数据（Task 15）— 未实现

**原计划内容：**
- `docker-compose.yml`：postgres（含 pgvector + pgcrypto）+ backend（uvicorn）+ frontend（next dev）
- `infra/postgres/init.sql` 已有；需补 compose 文件、`.env` 注入、健康检查
- 种子法条文本（`backend/data/seed/laws/*.txt`）供 `free-hr-ingest all` 使用
- `pnpm frontend dev` 热重载联调

**现状：** 仅有 `infra/postgres/init.sql`，需手动搭建 Postgres。无种子数据，新克隆仓库后 RAG 无内容可检索。

**实现工作量：** 约 2–3 h（compose 文件 + 至少 3 部示例法条文本）。

---

## 8. 评测集 + E2E Smoke（Task 16）— 未实现

**原计划内容：**
- `backend/data/eval/` 下 20 条问答对，覆盖劳动合同、工资、社保、离职等场景
- E2E smoke：启动真实服务 → 灌入种子数据 → 提问 → 断言引用非空
- 引用覆盖率、OOB 率指标脚本

**现状：** 无任何评测基础设施。

---

## 优先级建议

| 优先级 | 功能 | 理由 |
|--------|------|------|
| P0 | Docker Compose + 种子数据 | 没有这个，任何人克隆仓库后都无法跑起来 |
| P0 | 案例入库流程 | 当前 RAG 只有法条，案例场景完全空白 |
| P1 | 会话持久化 | 刷新丢失聊天记录，体验差 |
| P1 | SSE 流式 | 长问题等待 UX 差 |
| P1 | Auth 模块 | 生产环境必需；DB 表已就绪，实现成本低 |
| P2 | 前端完整版（shadcn + 登录 + 侧栏） | 体验提升，非最小可用门槛 |
| P2 | 集成测试（真实 DB） | 质量保障，需先有 Docker |
| P3 | 评测集 + E2E | 产品成熟度指标 |
