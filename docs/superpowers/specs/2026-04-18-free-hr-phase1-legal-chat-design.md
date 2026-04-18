# Free-HR Phase 1 设计文档：AI 法律咨询 MVP

- 日期：2026-04-18
- 作者：yanlinyi101
- 状态：Draft / 待实现

## 1. 产品背景

**Free-HR** 是面向中国大陆中小企业（HR、HR 主管、高管、老板）的用工合规 AI 助手，覆盖两大核心场景：

1. **AI 法律咨询**：用户用自然语言提问用工法律问题，系统基于法规/案例/司法指导知识库给出带引用溯源的合规解答。
2. **用工风险预警（可视化）**：用户上传员工花名册、劳动合同、员工手册、规章制度等，系统输出入职→在职→离职全周期风险看板。

整体按三阶段交付：

| 阶段 | 范围 |
|---|---|
| **Phase 1（本文档）** | 法律咨询 MVP：知识库摄入、RAG 对话、引用溯源、基础账号 |
| Phase 2 | 文档风险审查（合同/手册/规章制度） |
| Phase 3 | 员工全周期风险看板 |

本次只交付 Phase 1。Phase 2/3 各自独立 spec + plan + 实现循环。

## 2. Phase 1 目标与非目标

### 目标

- HR 登录后可以用自然语言向 AI 咨询中国大陆（以北京为首要适配地）用工法律问题。
- AI 回答必须基于已入库的法规/案例生成，答案中以内联编号 `[#n]` 标注引用，用户悬停引用可查看原文 chunk。
- 提供知识库冷启动数据集，覆盖以下范围：
  - 国家法：《劳动法》《劳动合同法》《劳动合同法实施条例》《社会保险法》《工伤保险条例》
  - 地方法规：《北京市工资支付规定》等北京市重点地方性法规
  - 司法解释：最高人民法院关于劳动争议的相关司法解释
  - 少量种子案例（Phase 1 不作为核心能力，Phase 2 扩展）
- 单租户自部署：`docker compose up` 一条命令跑起全栈。
- 评测集：10–20 个种子问题 + 期望引用的法条范围，用于手工回归。

### 非目标

- **不支持** 多租户 SaaS（Phase 1 之外考虑）。
- **不支持** 文档上传与风险审查（Phase 2）。
- **不支持** 员工花名册与全周期看板（Phase 3）。
- **不支持** 移动端原生 App（Web 响应式即可）。
- **不提供** 替代专业律师的法律意见，产品定位为"辅助参考"。

## 3. 技术栈与部署形态

| 层 | 选型 | 备注 |
|---|---|---|
| 后端 | Python 3.11 + FastAPI | 异步 + SSE 流式响应 |
| 前端 | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui | 聊天 UI、流式渲染、引用气泡 |
| 数据库 | PostgreSQL 16 + pgvector | 结构化数据与向量同库 |
| LLM | DeepSeek Chat（默认），通过 Provider 抽象可切换 Qwen / OpenAI / Claude | 环境变量配置 API key 与 model |
| Embedding | bge-m3（通过 SiliconFlow API，或后续支持本地部署） | 1024 维 |
| 认证 | JWT (HS256) + bcrypt | 单租户，角色：admin / hr |
| 部署 | Docker Compose | 服务：postgres、backend、frontend |
| 包管理 | 后端：uv；前端：pnpm | |

## 4. 系统架构

### 4.1 顶层结构

```
repo-root/
├── backend/              # Python FastAPI 应用
│   ├── src/free_hr/
│   │   ├── llm_gateway/        # LLM Provider 抽象
│   │   ├── knowledge_store/    # pgvector schema + 检索
│   │   ├── knowledge_ingest/   # CLI：分块 → embed → 入库
│   │   ├── chat/               # RAG 对话核心
│   │   ├── auth/               # 用户 / JWT / 角色
│   │   └── api/                # FastAPI 路由装配
│   ├── tests/
│   ├── data/                   # 法规原文种子数据（txt/jsonl）
│   └── pyproject.toml
├── frontend/             # Next.js 应用
│   ├── app/
│   │   ├── login/
│   │   ├── chat/
│   │   └── sources/
│   ├── components/
│   └── package.json
├── infra/
│   └── docker-compose.yml
├── docs/superpowers/     # spec / plan
└── README.md
```

### 4.2 模块边界

每个模块边界清晰、可独立测试。

#### llm_gateway

- **职责**：抽象不同 LLM 厂商的差异，统一暴露 `chat_stream(messages, **opts) -> AsyncIterator[str]` 和 `embed(texts) -> list[vector]`。
- **默认实现**：`DeepSeekProvider`（OpenAI 兼容接口）。
- **可插拔实现**（后续）：`QwenProvider`、`OpenAIProvider`、`ClaudeProvider`。
- **Embedding 实现**：`SiliconFlowEmbeddingProvider`（bge-m3）。
- **依赖**：`httpx`、env 配置。

#### knowledge_store

- **职责**：向量检索 + chunk 全文读取。
- **Schema**：`law_chunks`、`case_chunks`（见 §5.2）。
- **API（Python）**：
  - `search_laws(query_vec, k=8, region_filter=None) -> list[LawChunkHit]`
  - `search_cases(query_vec, k=4) -> list[CaseChunkHit]`
  - `get_chunk(chunk_id) -> LawChunk | CaseChunk`
- **依赖**：PostgreSQL + pgvector。

#### knowledge_ingest

- **职责**：从 `backend/data/` 下的原文语料生成分块、计算 embedding、写入 `law_chunks` / `case_chunks`，并在 `ingestion_runs` 记录。
- **形态**：独立 CLI（`uv run free-hr-ingest --source=laws/labor_contract_law.txt`），**不暴露 HTTP API**。
- **分块策略**：
  - 法条：按"第 X 条"硬切分，一条一个 chunk；长条文超过 800 字按子款再切。
  - 案例：按段落 + 重叠窗口（512 字、64 字 overlap）。
- **幂等**：同一 source_path + 内容 hash 已存在则跳过。

#### chat

- **职责**：RAG 对话核心业务逻辑。
- **流程**：见 §6。
- **Python API**：
  - `create_session(user_id, title) -> Session`
  - `stream_answer(session_id, user_message) -> AsyncIterator[ChatEvent]`
  - `list_sessions(user_id) -> list[Session]`
  - `list_messages(session_id) -> list[Message]`
- **依赖**：llm_gateway、knowledge_store。

#### auth

- **职责**：注册、登录、JWT 签发与校验、FastAPI 依赖注入。
- **角色**：
  - `admin`：首次启动通过环境变量 bootstrap；可创建 HR 子账号。
  - `hr`：普通用户，可使用咨询功能。
- **Phase 1 不实现**：密码重置邮件、MFA、OAuth。

#### api

- **职责**：装配 FastAPI 路由 + 中间件 + 异常处理，不写业务逻辑。

### 4.3 前端结构

- `app/login`：账号密码登录。
- `app/chat`：
  - 左栏：会话列表（新建、切换）。
  - 右栏：对话流；用户消息右对齐，AI 消息左对齐；AI 消息中 `[#n]` 渲染为可 hover 的引用气泡（hover 调用 `GET /api/knowledge/chunks/:id` 懒加载原文）。
  - 流式渲染：SSE 接收增量 token。
- `app/sources`：已入库法规列表（法名、章节数、条文数），点击查看法条目录树。

## 5. 数据模型

### 5.1 认证与对话

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'hr')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON chat_sessions (user_id, created_at DESC);

CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  citations_json JSONB,       -- assistant 消息：引用列表
  token_usage_json JSONB,     -- 模型返回的 usage
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON chat_messages (session_id, created_at ASC);
```

`citations_json` 结构：

```json
[
  {"idx": 1, "type": "law", "chunk_id": "...", "label": "劳动合同法·第三十九条"},
  {"idx": 2, "type": "case", "chunk_id": "...", "label": "(2023)京01民终123号"}
]
```

### 5.2 知识库

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE law_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  law_name TEXT NOT NULL,                 -- e.g. 中华人民共和国劳动合同法
  article_no TEXT,                        -- e.g. 第三十九条
  chapter TEXT,                           -- e.g. 第四章 劳动合同的解除和终止
  text TEXT NOT NULL,                     -- 条文正文
  effective_date DATE,                    -- 生效日期（用于版本标注）
  region TEXT NOT NULL DEFAULT 'national', -- national / beijing / ...
  source_url TEXT,
  content_hash TEXT NOT NULL,             -- 幂等用
  embedding vector(1024) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (law_name, article_no, region, content_hash)
);
CREATE INDEX ON law_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON law_chunks (region);

CREATE TABLE case_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_title TEXT NOT NULL,
  case_no TEXT,                           -- e.g. (2023)京01民终123号
  court TEXT,
  judgment_date DATE,
  text TEXT NOT NULL,
  tags TEXT[],
  source_url TEXT,
  content_hash TEXT NOT NULL,
  embedding vector(1024) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (case_no, content_hash)
);
CREATE INDEX ON case_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE ingestion_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT NOT NULL,              -- law / case
  source_path TEXT NOT NULL,
  status TEXT NOT NULL,                   -- pending / running / completed / failed
  stats_json JSONB,                       -- {chunks_created, chunks_skipped, errors}
  error_detail TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);
```

## 6. RAG 对话流水线

### 6.1 流程

```
用户提交 question → POST /api/chat/sessions/:id/messages
  1. 持久化 user message
  2. 查询改写：取最近 N=6 轮对话历史，调 LLM 生成独立 query（可选，Phase 1 先实现简单拼接，后续替换）
  3. Embedding：query → 1024 维向量
  4. 两路召回：
       - search_laws(query_vec, k=8, region_filter=['national','beijing'])
       - search_cases(query_vec, k=4)
  5. 合并：按相似度降序截断到 prompt 上下文预算 ~3000 token
  6. Prompt 装配（见 §6.2）
  7. LLM 流式生成（SSE 往前端转发 token）
  8. 流结束后解析 [#n] → 组装 citations_json，与完整 content 一起持久化 assistant message
  9. 将 citations_json 作为最终 SSE 事件发给前端
```

### 6.2 System Prompt（核心约束）

```
你是一名专注于中国大陆劳动法领域的合规咨询助手，主要服务中小企业的 HR 与管理层。

【引用规则】
- 只能基于下方 <context> 中提供的法条或案例作答，不得凭空引用其它法律条文。
- 每个结论性句子末尾必须以 [#n] 的形式标注引用来源编号（n 对应 <context> 中的条目编号）。
- 如 <context> 不足以回答该问题，直接说明"当前知识库暂无直接依据，建议咨询专业律师"，不要硬答。

【地域规则】
- 默认以国家法律和北京市地方规定为准。
- 若用户问题涉及其它地区，明确提示"以上答复基于国家层面规定，具体执行请参考当地地方法规"。

【风格】
- 回答简明扼要，先结论后依据。
- 面向非法律专业的 HR，避免堆砌法言法语。
- 涉及重大法律风险（如违法解除、未签合同双倍工资）时，明确提示风险等级。

<context>
[#1] 【劳动合同法·第三十九条】劳动者有下列情形之一的，用人单位可以解除劳动合同……
[#2] 【(2023)京01民终123号】……
...
</context>
```

### 6.3 引用解析

- 流结束后，用正则 `\[#(\d+)\]` 扫 assistant 完整文本。
- 去重后对每个 `n` 对应到 context 构建时的 `chunks[n-1]` 原始 chunk。
- 生成 `citations_json`（见 §5.1）。
- 若解析出的 `n` 超出 context 范围（LLM 幻觉），剔除该引用并在应用日志中打 `warning` 记录（含 session_id、message_id、越界编号）。Phase 1 不额外建审计表，后续阶段若需持久化审计再补。

## 7. API 界面

所有 `/api/*` 路径均需 JWT，除 `/api/auth/*`。

```
POST /api/auth/register         body: { email, password }  (仅 admin 可调用)
POST /api/auth/login            body: { email, password }  → { token, user }
GET  /api/auth/me

POST /api/chat/sessions         body: { title? }           → Session
GET  /api/chat/sessions                                    → [Session]
GET  /api/chat/sessions/:id/messages                       → [Message]
POST /api/chat/sessions/:id/messages (Content-Type: application/json,
                                      Accept: text/event-stream)
     body: { content: string }
     SSE events:
       - event: token       data: {"text": "...增量..."}
       - event: citations   data: [{"idx":1,...}]
       - event: done        data: {"message_id":"..."}
       - event: error       data: {"code":"...","message":"..."}

GET  /api/knowledge/chunks/:id                             → chunk 全文（给前端 hover 用）
GET  /api/knowledge/laws                                   → [LawSummary]
GET  /api/knowledge/laws/:name                             → 目录树
```

## 8. 错误处理

| 场景 | 处理 |
|---|---|
| LLM 超时 / 限流 / 5xx | SSE `error` 事件 + 前端显示"模型暂时不可用，点击重试"按钮；后端指数退避重试 2 次后放弃 |
| 检索零命中 | 不走 LLM？**走**。prompt 会告诉它 context 空→回复"建议咨询专业律师"。保证行为一致。 |
| 引用编号超出 context 范围 | 过滤掉该引用，记录告警日志，不向用户报错 |
| Embedding 服务不可用 | 返回 503 + 前端提示"知识库服务暂不可用" |
| 摄入流水线失败 | 事务回滚；`ingestion_runs.status=failed`，`error_detail` 写错误堆栈 |
| 用户越权访问他人会话 | 返回 404（不是 403，避免枚举会话 id） |

## 9. 测试策略

### 9.1 单元测试（pytest）

- `llm_gateway`：mock httpx，验证请求拼装与流式解析。
- `knowledge_ingest`：法条分块正确性（第 X 条切分、长条文子款切分、content_hash 幂等）。
- `chat`：prompt 装配、`[#n]` 引用解析（含越界过滤）。
- `auth`：密码 hash、JWT 签发与校验、角色依赖。

### 9.2 集成测试

- 用 `fake` LLM Provider 返回固定文本（含 `[#1][#2]`）。
- 起 testcontainer 级别 postgres + pgvector。
- 跑完整 chat 链路：创建会话 → 发消息 → 接收 SSE → 验证持久化内容与引用。

### 9.3 评测集（手工回归）

`backend/tests/eval/seed_questions.yaml` 列 10–20 个问题，每题含：

- `question`：用户问题
- `expected_laws`：期望命中的法条关键字（如 `劳动合同法·第三十九条`）
- `must_include_phrases`：必须出现的关键词（如"过失性解除"）
- `must_not_hallucinate`：不应出现的编造法条

每次改 prompt 或检索策略后跑一遍，手工 diff。

### 9.4 前端

- 组件测试（Vitest + React Testing Library）：引用气泡渲染、SSE 增量合并。
- E2E（Playwright，Phase 1 只保留登录 + 发一条消息的 smoke）。

## 10. 安全与合规

- 密码：bcrypt，cost=12。
- JWT：24h 过期，HS256，secret 来自 env。
- 会话隔离：所有 chat 查询均附带 `WHERE user_id = :current_user`，防越权。
- 速率限制：单用户 60 req/min（Phase 1 内存实现，后续 Redis）。
- **免责声明**：前端底部永久展示"本工具仅供参考，不构成法律意见"。首次登录弹窗确认。
- 日志：不记录用户原始提问内容到系统日志（只记 message_id 与时延），避免 PII 泄漏。

## 11. 部署

`infra/docker-compose.yml` 启动三个服务：

- `postgres`：pgvector/pgvector:pg16 镜像，持久卷。
- `backend`：Python 镜像，依赖 uv 装依赖，暴露 `:8000`。
- `frontend`：Node 镜像，`next start`，暴露 `:3000`。

环境变量（`.env.example`）：

```
POSTGRES_URL=postgresql://free_hr:free_hr@postgres:5432/free_hr
JWT_SECRET=change-me
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-too
LLM_PROVIDER=deepseek
LLM_API_KEY=
LLM_MODEL=deepseek-chat
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_API_KEY=
EMBEDDING_MODEL=BAAI/bge-m3
```

启动顺序：`docker compose up -d postgres` → `backend` 执行 migrations + bootstrap admin → `frontend`。

种子知识库摄入在首次启动后由 admin 通过 `docker compose exec backend uv run free-hr-ingest --all` 手动触发，便于观察日志。

## 12. 里程碑与验收

Phase 1 完成的标志：

1. `docker compose up` 起全栈。
2. admin 账号可登录，可创建 HR 账号。
3. `free-hr-ingest --all` 成功入库至少 6 部法规 + 1 部司法解释，`/api/knowledge/laws` 可列出。
4. HR 账号可在 `/chat` 页面发起对话，流式收到 AI 回答。
5. 回答中至少 80% 的结论性句子带 `[#n]` 引用，引用可 hover 看到原文。
6. 10–20 题评测集全部人工过一轮，记录结果。
7. 核心单元 + 集成测试通过。

## 13. 开放问题 / Phase 2+ 预留

- 地域扩展：Phase 2 需支持用户切换地域视角（上海/深圳等）。
- 多轮对话改写：Phase 1 先拼接上下文，后续可引入独立 query rewriter 模型。
- Reranker：当前只做向量相似度，后续可加 cross-encoder（如 bge-reranker-v2-m3）。
- 版本化法规：当前按 `effective_date` 标注，未来如劳动法修订需支持"问答时指定时间点"。
- Phase 2 文档风险审查与本阶段 chat 模块的集成：共享同一个 RAG 知识库与 LLM Gateway。
