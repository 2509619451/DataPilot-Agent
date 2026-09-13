# DataPilot-Agent V4 Final

DataPilot-Agent V4 是在 V3（LangGraph + Pandas/SQL + Python Sandbox + Visualization）基础上的最终工程化版本，新增：

- **FastAPI**：数据上传、会话、Agent 对话、SSE 执行流、图表、报告 API
- **Vue 3 + Vite**：正式 Web 前端，实时展示 Agent 执行过程
- **PostgreSQL**：数据集、会话、消息、运行日志、图表、报告持久化；上传数据同步成独立 SQL 表
- **Redis**：Dataset Profile 热缓存（可继续扩展会话/结果缓存）
- **LangGraph**：Planner → Executor → Verifier → Retry/Recovery → Chart → Reporter
- **Python Sandbox**：独立容器、只读数据卷、内部 Docker 网络、AST 白名单、超时、CPU/内存限制
- **Docker Compose**：frontend / backend / postgres / redis / python-sandbox 一键启动

## 1. V4 对 V3 的兼容修复

### 1.1 图表字段不再硬编码

V3 中类似 `total_sales` / `total_profit` 不存在时会导致图表失败。V4 的 `chart_tool.py` 会直接读取工具实际返回的 records，并自动解析分类轴与数值轴，例如 `sum_sales`、`mean_profit`，即使 Planner 给了错误 y 字段也会自动回退到真实数值字段。

### 1.2 summary_statistics 支持多列

```json
{
  "columns": ["sales", "profit"]
}
```

一次返回两列完整的 count / mean / median / std / min / max / Q1 / Q3，不再发生“重试后只覆盖一列”的问题。

### 1.3 Verifier 区分已恢复与未恢复错误

- `resolved_errors`：经过自动修复后已经成功的历史错误
- `errors`：超过最大重试次数后仍然失败的错误

Reporter 的 `limitations` **只读取 `errors`**，不会再把已恢复错误误报成最终限制。

## 2. 目录结构

```text
datapilot-agent-v4-final/
├── backend/
│   ├── app/
│   │   ├── api/                  # datasets / sessions / chat / charts / reports
│   │   ├── agent/                # LangGraph nodes
│   │   ├── core/                 # settings / PostgreSQL / Redis
│   │   ├── models/               # SQLAlchemy entities + Pydantic schemas
│   │   ├── services/             # dataset / session / agent / report
│   │   ├── tools/                # Pandas / SQL / Python / Chart
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── api.js
│   │   ├── main.js
│   │   └── style.css
│   ├── nginx.conf
│   └── Dockerfile
├── sandbox/
│   ├── app.py
│   ├── runner.py
│   └── Dockerfile
├── data/uploads/
├── outputs/charts/
├── outputs/reports/
├── docker-compose.yml
├── .env.example
└── Makefile
```

## 3. 启动

### 3.1 创建环境变量

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

Linux / macOS：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的Key
DEEPSEEK_MODEL=deepseek-v4-flash
```

> 如果你的 DeepSeek 账号/网关使用官方稳定模型名，可把 `DEEPSEEK_MODEL` 改成 `deepseek-chat`。没有 API Key 时系统仍可用内置启发式 Planner 跑基础演示，但复杂自然语言分析建议配置模型。

### 3.2 Docker 启动

```bash
docker compose up --build
```

访问：

- 前端：`http://localhost:8080`
- FastAPI Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 4. API

### 上传数据

```http
POST /api/datasets/upload
Content-Type: multipart/form-data
```

### 获取 Profile

```http
GET /api/datasets/{dataset_id}/profile
```

### 普通 Agent 对话

```http
POST /api/chat
Content-Type: application/json

{
  "dataset_id": "...",
  "session_id": null,
  "message": "哪个地区销售额最高？"
}
```

### SSE 实时 Agent 对话

```http
POST /api/chat/stream
```

事件类型：

```text
session -> trace -> trace -> ... -> done
```

前端会实时显示：

```text
start
planner
executor
verifier
executor/retry ...
chart
reporter
```

### 会话

```http
POST /api/sessions
GET  /api/sessions/{session_id}
```

### 图表

```http
GET /api/charts/{chart_id}
```

### 报告

```http
POST /api/reports
GET  /api/reports/{report_id}
```

## 5. Agent 工具

- `get_dataset_schema`
- `summary_statistics`
- `groupby_aggregate`
- `filter_data`
- `correlation_analysis`
- `time_series_analysis`
- `detect_outliers`
- `query_database`
- `run_python`
- Chart Node（基于真实工具结果 records 自动绘图）

## 6. LangGraph 工作流

```text
START
  ↓
Planner
  ↓
Executor
  ↓
Verifier ──失败且可恢复──→ Executor
  │
  ├──下一步骤──────────→ Executor
  │
  └──全部完成
        ↓
      Chart
        ↓
     Reporter
        ↓
       END
```

每个分析步骤最多自动重试 `MAX_RETRY=2` 次。超过重试次数后记录为 unresolved error，但不会阻塞其他可独立执行的分析步骤。

## 7. PostgreSQL 数据模型

### `datasets`

保存数据集 ID、原文件路径、SQL 表名、Profile、行列数。

### `chat_sessions` / `messages`

保存多轮对话上下文。

### `analysis_runs`

保存：

- question
- plan
- tool_calls
- tool_results
- errors
- resolved_errors
- charts
- final_answer
- execution_ms

### `charts` / `reports`

持久化图表与报告元信息。

每个上传数据集还会创建一张：

```text
dataset_<16位ID>
```

供只读 SQL Tool 查询。

## 8. Redis

当前 V4 将 Dataset Profile 缓存为：

```text
dataset:profile:<dataset_id>
```

TTL 默认 1 小时。PostgreSQL 始终是真实持久化来源，Redis 缓存丢失不会影响数据正确性。

## 9. Python Sandbox 安全策略

- Sandbox 与外部网络隔离，只通过内部 Docker network 与 backend 通信
- 数据目录只读挂载
- 容器 `read_only: true`
- `no-new-privileges`
- drop ALL Linux capabilities
- 512 MB 内存限制
- 1 CPU
- 执行超时默认 8 秒
- AST 拦截：`open/eval/exec/__import__/os/sys/subprocess/socket/...`
- 仅允许 pandas / numpy / math / statistics
- DataFrame 通过预置变量 `df` 使用

高级分析代码应写入变量 `result`：

```python
result = df.groupby("region")["sales"].sum().sort_values(ascending=False)
```

## 10. 测试

Docker：

```bash
make test
```

或进入 backend 环境：

```bash
pytest -q
```

已包含：

- 多列描述统计测试
- groupby 动态 value_field 测试
- 图表字段自动回退测试
- SQL 写操作/跨表访问拦截测试

## 11. 本地非 Docker 开发

后端仍需要 PostgreSQL 和 Redis。可以只启动基础设施：

```bash
docker compose up postgres redis python-sandbox
```

然后：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

Vite 会把 `/api` 代理到 `http://localhost:8000`。

## 12. 一次完整验证

上传一个包含：

```text
region, sales, profit
```

的 CSV，然后依次提问：

```text
1. 分析各地区销售额和利润情况，并生成图表
2. sales 和 profit 的描述性统计是什么？
3. 哪个地区销售额最高？
4. 找出 profit 的异常值
```

重点检查：

- `summary_statistics` 是否同时返回 sales + profit
- 图表 y 字段是否使用工具真实返回的 `sum_sales` / `sum_profit` 等，而非硬编码字段
- 发生字段错误并恢复后，最终 `limitations` 是否为空
- PostgreSQL 的 `analysis_runs` 是否完整保存 plan/tool_calls/tool_results
- Vue 页面是否实时显示 Agent trace
