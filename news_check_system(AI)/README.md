# RAG_NEW —— 基础 RAG（LangChain + Milvus）

按步骤从零做一个精简 RAG。**当前：混合检索（向量+BM25→RRF→Rerank）+ 官方 ragas 评估**。
代码按职责拆分模块，工程化可维护。

## 目录结构

```
RAG_NEW/
├── main.py          # 问答入口/收集模式：加载→建索引→逐题问答 / 生成 collected_v1.json（PyCharm 运行）
├── ai_server.py     # HTTP 服务入口：把主链路包装成 /api/ai/chat 接口，供前端 AI对话页调用（端口 8001）
├── evaluate.py      # 评估入口：官方 ragas 框架（读 标准集+收集结果 → ragas.evaluate → 报告）
├── config.py        # 全局配置：.env 加载 + Milvus/模型/数据路径常量
├── loader.py        # 知识侧：文档解析 + 切块 + source 来源绑定
├── embeddings.py    # 模型侧：向量化模型客户端（Qwen3-Embedding-0.6B）
├── reranker.py      # 模型侧：Rerank 精排（bge-reranker-v2-m3，网络异常自动降级）
├── vector_store.py  # 检索层：Milvus 连接/建集合/入库 + 混合检索
│                    #   （向量路+BM25 → RRF 融合 → Rerank 精排；retrieve 接口不变）
├── generator.py     # 生成侧：提示词组装 + DeepSeek 回答（附参考来源）
├── requirements.txt       # 问答链路依赖
├── requirements-eval.txt  # 官方 ragas 评估依赖（建议独立 venv 安装）
├── .env.example     # 密钥模板（复制为 .env 填入）
├── .env             # 实际密钥
├── evals/           # 评估数据与结果
│   ├── eval_set_v1.json     # 标准集（顶层数组）：[{question, ground_truths:[标准答案]}]
│   ├── collected_v1.json    # 收集结果（顶层数组）：[{question, answer, contexts:[检索片段]}]
│   └── ragas_report_v1.json # 评估报告（evaluate.py 生成：官方 ragas 各指标分数）
└── data/
    ├── doc_a_clean.md    # 知识源1：产品/技术手册（含 Markdown 标题层级）
    └── doc_b_clean.csv   # 知识源2：FAQ/错误码记录表（135 条）
```

## 运行方式（PyCharm）

1. 用 PyCharm 打开 `RAG_NEW` 文件夹，解释器选 `D:\miniconda\envs\langchain1.2\python.exe`
2. **问答**：运行 `main.py`（想换问题改顶部 `DEMO_QUESTIONS`；想重建索引把 `REBUILD=True`）
3. **评估（官方 ragas 框架，两步）**：
   - 第 1 步 收集：运行 `main.py` 前把顶部 `COLLECT_EVAL_DATA` 改成 `True`（或设环境变量
     `COLLECT_EVAL=1`）→ 对标准集每个问题跑一遍主链路，把 answer / contexts 按顺序
     存成 `evals/collected_v1.json`；也可手工整理同构 JSON
   - 第 2 步 打分：`evaluate.py` 按顺序 zip 两份文件 → 拼成 question/answer/contexts/
     ground_truths 数据集 → `ragas.evaluate(...)` → `evals/ragas_report_v1.json`
   - 官方 ragas 与主环境 langchain 1.2 冲突，需独立 venv 安装：
     `python -m venv .venv-eval` → `.venv-eval\Scripts\pip install -r requirements-eval.txt`
     → `.venv-eval\Scripts\python evaluate.py`

## 作为 HTTP 服务对接前端（智能客服）

前端「AI对话」页已经预留了客服接口：`POST {AI_BASE_URL}/api/ai/chat`，默认指向
`http://localhost:8001`（见前端 `js/config.js` 的 `AI_BASE_URL`）。本模块的
`ai_server.py` 就是把这个接口接上主链路，**让前端直接调用 RAG 问答**。

1. 启动 Milvus 服务（默认 `http://localhost:19530`）
2. 确认 `.env` 中 `SI_API_KEY` / `DEEPSEEK_API_KEY` 有效
3. 用 RAG 主环境运行（例如 `D:\miniconda\envs\langchain1.2\python.exe`）：

   ```bash
   python ai_server.py
   # 或：uvicorn ai_server:app --host 0.0.0.0 --port 8001
   ```

接口约定（与前端 `js/api.js` 的 `API.chat()` 一致）：

- `POST /api/ai/chat`，body `{"question": "如何注册账号？"}` → `{"code":200,"message":"success","data":{"answer":"..."}}`
- `POST /api/ai/init`：修改 `data/` 知识文件后强制重建索引
- `GET /`：健康检查

容错：问候语直接回复；提问前先 TCP 探测 Milvus 可达性，不可达立即返回友好提示；
建库/问答都在线程池中带超时执行，前端不会一直「正在思考」。

## 模块职责

```
main.py          问答/收集：load_chunks → build_index
 │               问答模式：循环 retrieve + ask（DEMO_QUESTIONS）
 │               收集模式：对标准集问题跑 retrieve + ask → evals/collected_v1.json
 ├─ loader.py        读 doc_a+doc_b → 切块，每个 chunk 绑定 source（章节路径 / 记录 code）
 ├─ embeddings.py    get_embeddings()：文本向量模型
 ├─ reranker.py      rerank(query, texts, top_n)：Cross-Encoder 精排（失败自动降级原序）
 ├─ vector_store.py  build_index()：text+source+vector 写入 Milvus（幂等跳过）
 │                   retrieve()：向量路(Milvus) + BM25 词法路 → RRF 融合 → Rerank
 │                   → (文本, 来源, 分数)（接口不变）
 └─ generator.py     ask()：片段拼提示词 → DeepSeek 回答，末尾输出「参考来源」

evaluate.py      官方 ragas：读两份数组文件 → zip 拼成
                  [question, answer, contexts, ground_truths, reference]
                  → ragas.evaluate(...) → evals/ragas_report_v1.json（不跑主链路）
```

## 向量库：Milvus（默认 localhost:19530）

- 独立库 `rag_new` / 集合 `doc_chunks`，HNSW / COSINE / 1024 维（不影响 `AI_rag` 等已有库）
- 每条记录 = 自增 id + text 文本 + source 来源 + vector 向量
- source：FAQ/错误码行存 `FQA-101`/`ERR-108`；手册段落存 `《产品手册》> 二、账号体系与安全 > 2.1 注册与开户`
- 幂等：集合已存在且条数一致则跳过向量化；`REBUILD=True` 强制重建

## 评测（官方 ragas 框架，收集与打分分离）

- **标准集** `evals/eval_set_v1.json`：顶层数组，每条只有 `question`（问题）+
  `ground_truths`（标准答案列表，RAGAS 要求数组）；库外负例 `ground_truths=[]`（不参与打分）
- **收集结果** `evals/collected_v1.json`：顶层数组，每条只有 `question` + `answer`（模型答案）+
  `contexts`（检索片段原文）——由问答侧跑一遍产生，评估**不自己跑 RAG**
- **`evaluate.py` 就三件事**：按顺序 zip 两份文件 → 拼成 ragas 四列数据集 → 调官方 ragas：
  ```python
  rows = [{"question": c["question"], "answer": c["answer"], "contexts": c["contexts"],
           "ground_truths": s["ground_truths"], "reference": s["ground_truths"][0]}
          for s, c in zip(std, col)]                      # 两文件都无 id 等附加字段，zip 即可
  ragas.evaluate(Dataset.from_list(rows),
                 metrics=[faithfulness, answer_relevancy,
                          context_precision, context_recall],
                 llm=DeepSeek, embeddings=Qwen3/SiliconFlow)
  ```
  指标口径、判官提示词等都由 ragas 框架内部处理，不再手写"伪 RAGAS"判官
- 结果含逐例分数与均值，方便对不同检索策略（如后续混合检索）做同一框架下对比

## 实测输出示例（问答，自动带参考来源）

- `如何注册账号？` → …回答… 参考来源：FQA-101、《产品手册》> 二、账号体系与安全 > 2.1 注册与开户
- `账号被锁定（ERR-108）怎么解锁？` → …回答… 参考来源：ERR-108、ERR-107

下一步等你指示（例如：按你的思路加混合检索 / Rerank 后再对比评估）。
