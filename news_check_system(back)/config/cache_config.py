import os

import redis.asyncio as redis
import json

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

#创建redis连接对象
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    protocol=2
)

#获取字符串类缓存
async def get_cache(key: str):
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f'缓存获取错误，错误信息为{e}')
        return None

#获取json类缓存
async def get_json_cache(key: str):
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        else:
            return None
    except Exception as e:
        print(f'获取缓存错误，错误信息为{e}')
        return None

#设置缓存
async def set_cache(key: str, value: str, expire: int=3600):
    try:
        if isinstance(value,(dict,list)):
            value = json.dumps(value,default=str)
        await redis_client.setex(key,expire,value)
        return True
    except Exception as e:
        print(f'缓存设置错误，错误信息为{e}')
        return False
