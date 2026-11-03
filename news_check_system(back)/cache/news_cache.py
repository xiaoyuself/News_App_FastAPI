from typing import Any, Dict, List, Optional

from config.cache_config import get_json_cache, set_cache

CATEGORIES_KEY = 'news:categories'
NEWS_LIST_PREFIX = 'news_list'


def _list_key(category_id: Optional[int], page: int, size: int) -> str:
    """列表缓存 key：news_list:分类:页码:每页条数。

    必须带分隔符 —— 原来直接拼成 f'news_list:{cat}{page}{size}'，
    分类 1 的第 21 页(size=10) 与 分类 12 的第 1 页(size=10) 都会变成
    "news_list:12110"，两个完全不同的列表会互相覆盖（读到别人的数据）。
    """
    return f'{NEWS_LIST_PREFIX}:{category_id}:{page}:{size}'


#创建新闻种类缓存
async def set_cached_categories(data:List[Dict[str,Any]],expire:int=7200):
    return await set_cache(CATEGORIES_KEY,data,expire)

#获取新闻种类缓存的数据
async def get_cached_categories():
    return await get_json_cache(CATEGORIES_KEY)

#创建新闻列表缓存
async def set_cache_news_list(category_id:Optional[int],page:int,size:int,news_list:List[Dict[str,Any]],expire:int=300):
    return await set_cache(_list_key(category_id, page, size),news_list,expire)

#获取新闻列表换粗拿数据
async def get_cache_news_list(category_id:Optional[int],page:int,size:int):
    return await get_json_cache(_list_key(category_id, page, size))