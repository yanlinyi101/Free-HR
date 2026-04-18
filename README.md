# Free-HR

面向中国大陆中小企业的用工合规 AI 助手。

## 产品定位

为 HR、HR 主管、高管、老板提供：

1. **AI 法律咨询**：自然语言提问用工法律问题，回答基于法规/案例知识库，带引用溯源。
2. **用工风险预警（可视化）**：上传员工花名册、劳动合同、员工手册、规章制度，覆盖入职→在职→离职全周期风险预警。

默认适配地域：中国大陆，北京为主。

## 交付阶段

| 阶段 | 范围 | 状态 |
|---|---|---|
| **Phase 1 MVP** | 无鉴权 RAG 问答：`POST /api/chat` + 引用抽屉 | 后端 + 前端已实现 |
| Phase 1 完整版 | 账号、会话历史、SSE 流式、部署编排 | 未开始 |
| Phase 2 | 文档风险审查（合同 / 手册 / 规章制度） | 未开始 |
| Phase 3 | 员工全周期风险看板 | 未开始 |

## 快速开始（MVP）

前置：Python 3.11、Node ≥ 20（推荐 pnpm）、Postgres 16 + pgvector 扩展、一个可用的 LLM/Embedding API Key（默认 DeepSeek + SiliconFlow）。

### 1. 启动 Postgres

自行部署或使用云服务，确保已开启 `vector` 与 `pgcrypto` 扩展。可参考 `infra/postgres/init.sql`。

### 2. 配置环境

```bash
cp .env.example backend/.env
# 填入 LLM_API_KEY、EMBEDDING_API_KEY、POSTGRES_URL
```

### 3. 后端

```bash
cd backend
uv sync                                        # 安装依赖
uv run alembic upgrade head                    # 建表 + pgvector
uv run free-hr-ingest all                      # 灌入示例法条（需要嵌入 API）
uv run uvicorn free_hr.api.main:app --reload   # 默认 :8000
```

健康检查：`curl http://localhost:8000/api/health` → `{"status":"ok"}`

### 4. 前端

```bash
cd frontend
cp .env.local.example .env.local               # 默认指向 http://localhost:8000
pnpm install
pnpm dev                                       # 默认 :3000
```

浏览器访问 <http://localhost:3000> 即可开始提问。

## 测试

```bash
cd backend
uv run pytest tests/unit/                      # 22 个单元测试
uv run pytest tests/integration/test_api_endpoints.py  # 4 个 API 集成测试（无需真 DB）
# 其他 tests/integration/ 下的用例需要真实 Postgres + pgvector
```

## 当前 MVP 不包含

- 账号 / 登录 / 多租户（所有请求匿名）
- 会话历史持久化（每次刷新从空白开始）
- SSE / 流式响应（后端一次性返回完整 JSON，前端做打字机效果）
- Docker Compose 编排
- 评测集与 E2E smoke
- 合同 / 手册 / 员工生命周期模块（Phase 2–3）

这些功能在完整版计划中，见 `docs/superpowers/plans/2026-04-18-free-hr-phase1-legal-chat.md`。

## API 概览（MVP）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat` | 单轮 RAG 问答，body `{"content": string}` |
| GET | `/api/knowledge/chunks/{id}` | 获取法条/案例原文（供引用抽屉调用） |
| GET | `/api/knowledge/laws` | 已入库法律列表 |

## 设计文档

- [Phase 1 完整版设计](docs/superpowers/specs/2026-04-18-free-hr-phase1-legal-chat-design.md)
- [Phase 1 实现计划（完整版）](docs/superpowers/plans/2026-04-18-free-hr-phase1-legal-chat.md)

## 免责声明

本工具输出内容仅供参考，不构成法律意见。重大法律事项请咨询专业律师。
