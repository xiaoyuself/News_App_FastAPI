import os

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession,create_async_engine

ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    'mysql+aiomysql://root:Li123456789@localhost:3306/news_app?charset=utf8mb4'
)

# 是否打印每条 SQL（默认关闭：日志量大、高并发时明显拖慢；排查问题时设 SQL_ECHO=1 打开）
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"

#创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=SQL_ECHO,
    pool_size = 10,
    max_overflow = 20,
    # 连接最多复用 1 小时就回收重建：MySQL 默认 8 小时会主动断开空闲连接，
    # 不回收的话应用会拿到一条"已经死了"的连接，接口偶发 500（重启服务才恢复）
    # 注：这里用 pool_recycle 而不是 pool_pre_ping —— aiomysql 0.3.x 改了 ping() 的签名，
    #     开 pool_pre_ping 会直接抛 TypeError，换成回收时间更稳妥且跨版本都能跑
    pool_recycle = 3600
)

#创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_ = AsyncSession,
    expire_on_commit = False
)

#获取会话函数
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

