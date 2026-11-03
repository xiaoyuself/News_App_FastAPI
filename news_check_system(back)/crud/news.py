from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import set_cached_categories, get_cached_categories, get_cache_news_list, set_cache_news_list
from models.news import Categories, News

# 列表页只需要这几列，不查 content（正文）：
# 一条正文几百~几千字，10 条一起返回会让列表接口体积涨 5~10 倍，而列表页根本用不到正文
LIST_COLUMNS = (News.id, News.title, News.description, News.image,
                News.author, News.category_id, News.views, News.publish_time)


def _row_to_dict(row) -> dict:
    """把"只查了部分列"的查询结果转成和原来字段名一致的 dict（保持 snake_case）。"""
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "image": row.image,
        "author": row.author,
        "category_id": row.category_id,
        "views": row.views,
        "publish_time": row.publish_time,
    }


#获取新闻种类
async def get_Categories(session:AsyncSession,skip:int=0,limit:int=100):
    #先通过缓存获取新闻种类
    cached_categoried = await get_cached_categories()
    if cached_categoried:
        return cached_categoried
    #缓存中没有数据则查询数据库
    # 按 sort_order 排序：分类栏顺序应该由运营配置决定，而不是碰巧按 id（插入顺序）排
    order = select(Categories).order_by(Categories.sort_order, Categories.id).offset(skip).limit(limit)
    res = await session.execute(order)
    categories = res.scalars().all()
    #将查询数据库得到的数据存入缓存
    if categories:
        categories = jsonable_encoder(categories)
        await set_cached_categories(categories)
    #返回新闻种类数据
    return categories


#获取新闻列表
async def get_news_list(session:AsyncSession,category_id:int=1,skip:int=0,limit:int=10):
    #从缓存中获取新闻列表
    page = skip//limit+1
    cached_list = await get_cache_news_list(category_id,page,limit)
    if cached_list:
        return cached_list
    #缓存中没有则从数据库中找
    # 必须显式 ORDER BY：不写排序时 MySQL 的返回顺序是"不保证"的（现在看着像按 id，
    # 数据量变大或换了索引后就会变），翻页会出现重复条/漏条；新闻列表按发布时间倒序才符合直觉
    order = (select(*LIST_COLUMNS)
             .where(News.category_id==category_id)
             .order_by(News.publish_time.desc(), News.id.desc())
             .offset(skip).limit(limit))
    res = await session.execute(order)
    news_list = [_row_to_dict(row) for row in res.all()]
    #将数据库中找到的数据存入缓存
    if news_list:
        news_list = jsonable_encoder(news_list)
        await set_cache_news_list(category_id,page,limit,news_list)
    #返回新闻列表
    return news_list


#获取新闻总数
async def get_news_count(session:AsyncSession,category_id:int=1):
    order = select(func.count(News.id)).where(News.category_id==category_id)
    res = await session.execute(order)
    return res.scalar_one()


#获取新闻详情
async def get_news_detail(session:AsyncSession,news_id:int):
    order = select(News).where(News.id==news_id)
    res = await session.execute(order)
    return res.scalar_one_or_none()


#增加浏览量
async def increase_view_count(session:AsyncSession,news_id:int):
    order = update(News).where(News.id==news_id).values(views = News.views + 1)
    res = await session.execute(order)
    await session.commit()
    #返回是否修改成功
    return res.rowcount > 0


#获取推荐新闻
async def get_related_news(session:AsyncSession,news_id:int,category_id:int,limit:int=5):
    #获取同种类、排除当前这条、浏览量最高的 limit 条
    # 推荐位只需要标题/时间/浏览量，同样不查正文（原来把 5 篇正文全塞进了详情响应）
    order = (select(*LIST_COLUMNS)
             .where(News.category_id==category_id, News.id != news_id)
             .order_by(News.views.desc(), News.id.desc())
             .limit(limit))
    res = await session.execute(order)
    related_news = res.all()
    #返回推荐的五条新闻信息
    return [
        {
            "id": news_detail.id,
            "title": news_detail.title,
            "description": news_detail.description,
            "image": news_detail.image,
            "author": news_detail.author,
            "publishTime": news_detail.publish_time,
            "categoryId": news_detail.category_id,
            "views": news_detail.views,
        }
    for news_detail in related_news]
