# 新闻资讯平台（内置 RAG 智能客服）

一个可私有化部署的新闻资讯应用：新闻浏览、用户体系、收藏与浏览历史，并内置基于 RAG 的智能客服。

## 功能

| 模块 | 功能 |
|---|---|
| 新闻 | 分类切换、分页列表（按发布时间倒序）、详情页、同类推荐、浏览量统计 |
| 用户 | 注册、登录（token 鉴权）、资料修改、密码修改 |
| 互动 | 收藏 / 取消收藏、浏览历史记录 |
| 智能客服 | 基于知识库的问答：混合检索（向量 + BM25 + RRF + 精排）→ 大模型生成 → 置信度兜底 |
| 知识库 | 支持 Markdown 手册、CSV 记录表、**PDF 文档**（文本页直读，图片页 OCR） |
| 对话 | 支持多轮追问（携带最近 3 轮上下文，检索前自动补全指代） |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | 原生 HTML / CSS / JavaScript（无构建依赖，手机风格单页 + hash 路由） |
| 后端 | Python 3.12、FastAPI、SQLAlchemy（异步）、aiomysql、Pydantic |
| 存储 | MySQL 8（业务数据）、Redis 7（分类/列表缓存） |
| 智能客服 | LangChain、Milvus（服务模式 / milvus-lite 二选一）、DeepSeek（生成）、硅基流动（Embedding / Rerank） |
| PDF 解析 | PyMuPDF（文本与图片区域提取）、RapidOCR（扫描件 OCR，纯 CPU） |

## 目录结构

```
.
├── news_check_system(front)/     前端：原生 SPA
│   ├── index.html                入口页面
│   ├── css/  js/                 样式与脚本（api / router / views）
│   └── nginx.conf                静态资源 + /api/ 反向代理配置
├── news_check_system(back)/      后端：FastAPI
│   ├── main.py                   入口（挂载路由、异常处理、GZip、CORS）
│   ├── config/                   数据库与 Redis 配置（读环境变量）
│   ├── routers/                  路由层
│   ├── crud/                     数据访问层
│   ├── models/                   SQLAlchemy ORM 模型（表结构定义在这里）
│   ├── schemas/                  Pydantic 出入参模型
│   ├── utils/                    鉴权、密码哈希、统一响应、全局异常
│   └── requirements.txt
└── news_check_system(AI)/        智能客服：RAG 服务
    ├── ai_server.py              HTTP 服务入口（/api/ai/chat、/api/ai/init）
    ├── main.py                   命令行问答 / 评估数据收集
    ├── loader.py                 知识加载与切块（md + csv + pdf）
    ├── pdf_loader.py             PDF 逐页解析：类型判定、文本提取、OCR
    ├── vector_store.py           建索引 + 混合检索（向量 + BM25 → RRF → 精排）
    ├── embeddings.py             向量模型客户端
    ├── reranker.py               精排模型客户端
    ├── generator.py              提示词组装与回答生成
    ├── query_rewrite.py          Multi-Query 与多轮指代改写
    ├── config.py                 全局配置（读 .env 与环境变量）
    ├── data/                     知识库文件（Markdown 手册、CSV 记录表、pdf/ 目录）
    ├── evals/                    评估标准集与结果（ragas）
    └── requirements.txt
```

## 快速开始

### 1. 准备依赖服务

- **MySQL 8**：建库 `news_app`。表结构见 `news_check_system(back)/models/` 下的 ORM 模型
  （建库脚本与初始演示数据不在本仓库，请自行准备）
- **Redis 7**：用于新闻分类 / 列表缓存。**建议先启动 Redis 再启动后端**
  （缓存异常会被捕获并降级到数据库，但首次连接失败会拖慢首个请求）

### 2. 配置密钥

```bash
cp "news_check_system(AI)/.env.example" "news_check_system(AI)/.env"
# 填入硅基流动与 DeepSeek 的 API Key
```

### 3. 启动三个服务

```bash
# 后端（8000）
cd "news_check_system(back)"
pip install -r requirements.txt
uvicorn main:app --port 8000

# 智能客服（8001）
cd "news_check_system(AI)"
pip install -r requirements.txt
python ai_server.py

# 前端（8080）：任意静态服务器
cd "news_check_system(front)"
python -m http.server 8080
```

浏览器打开 `http://localhost:8080`。前端 `js/config.js` 会自动判断环境：
本机访问时直连 8000 / 8001，通过域名或 IP 访问时走同源（由 nginx 转发）。

### 4. 构建知识库索引

```bash
curl -X POST http://127.0.0.1:8001/api/ai/init
```

首次启动也会自动建索引。**修改 `data/` 下的知识文件后，请再次调用该接口**（会强制重建，
扫描件 PDF 需要逐页 OCR，一本 200 页的书约 10 分钟）。

## 智能客服说明

- **知识来源**：`news_check_system(AI)/data/` 下的 `doc_a_clean.md`（手册）、
  `doc_b_clean.csv`（FAQ / 错误码）、`pdf/` 目录（PDF 文档）
- **PDF 处理**：逐页判定类型 —— 文字多的页直接提取文字；整页是图的页渲染后走 OCR；
  文字与图片混排的页会把两者按页面坐标合并，再按阅读顺序拼接
- **来源标注**：检索片段会带来源（`FQA-101` / `《文件名》第 N 页` / 手册章节路径），
  回答末尾会列出生效的来源
- **向量库**：默认连独立 Milvus 服务（`MILVUS_MODE=server`）；小内存机器可用
  `MILVUS_MODE=lite` + `MILVUS_LITE_PATH` 指向本地 `.db` 文件，省掉一个容器
- **评估**：`main.py` 收集答案 → `evaluate.py` 用官方 ragas 打分，
  指标为 faithfulness / answer_relevancy / context_precision / context_recall

## 注意

- `.env` 含 API Key，**已被 `.gitignore` 排除**，请按 `.env.example` 自行配置
- 智能客服依赖外网（Embedding、Rerank、生成均为云端 API）；断网时新闻功能正常，客服不可用
- 数据库默认口令仅用于本地/演示，部署到公网请务必修改
