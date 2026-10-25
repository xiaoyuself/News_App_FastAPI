from typing import Any, Dict, List, Optional

from config.cache_config import get_json_cache, set_cache

CATEGORIES_KEY = 'news:categories'
NEWS_LIST_PREFIX = 'news_list:'

#创建新闻种类缓存
async def set_cached_categories(data:List[Dict[str,Any]],expire:int=7200):
    return await set_cache(CATEGORIES_KEY,data,expire)

#获取新闻种类缓存的数据
async def get_cached_categories():
    return await get_json_cache(CATEGORIES_KEY)

#创建新闻列表缓存
async def set_cache_news_list(category_id:Optional[int],page:int,size:int,news_list:List[Dict[str,Any]],expire:int=1200):
    key = f'{NEWS_LIST_PREFIX}{category_id}{page}{size}'
    return await set_cache(key,news_list,expire)

#获取新闻列表换粗拿数据
async def get_cache_news_list(category_id:Optional[int],page:int,size:int):
    key = f'{NEWS_LIST_PREFIX}{category_id}{page}{size}'
    return await get_json_cache(key)