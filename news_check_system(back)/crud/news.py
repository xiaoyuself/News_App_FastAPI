from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import set_cached_categories, get_cached_categories, get_cache_news_list, set_cache_news_list
from models.news import Categories, News

#获取新闻种类
async def get_Categories(session:AsyncSession,skip:int=0,limit:int=100):
    #先通过缓存获取新闻种类
    cached_categoried = await get_cached_categories()
    if cached_categoried:
        return cached_categoried
    #缓存中没有数据则查询数据库
    order = select(Categories).offset(skip).limit(limit)
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
    order = select(News).where(News.category_id==category_id).offset(skip).limit(limit)
    res = await session.execute(order)
    news_list = res.scalars().all()
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
    #获取五条同种类的不同的五条浏览量最高的新闻
    order = select(News).where(News.category_id==category_id,News.id != news_id).order_by(News.views.desc()).limit(limit)
    res = await session.execute(order)
    related_news = res.scalars().all()
    #返回推荐的五条新闻信息
    return [
        {
            "id": news_detail.id,
            "title": news_detail.title,
            "content": news_detail.content,
            "image": news_detail.image,
            "author": news_detail.author,
            "publishTime": news_detail.publish_time,
            "categoryId": news_detail.category_id,
            "views": news_detail.views,
        }
    for news_detail in related_news]