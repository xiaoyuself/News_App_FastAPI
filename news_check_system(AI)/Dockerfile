FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 只拷运行时需要的模块和知识库文件（.env 由 compose 注入，不进镜像）
COPY config.py ai_server.py loader.py embeddings.py vector_store.py \
     reranker.py generator.py query_rewrite.py ./
COPY data ./data

EXPOSE 8001

CMD ["uvicorn", "ai_server:app", "--host", "0.0.0.0", "--port", "8001"]
