from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.favorite import Favorite
from models.news import News


#通过数据库查询新闻收藏状态
async def is_news_favorite(
        session:AsyncSession,
        user_id: int,
        news_id: int,
):
    #根据用户id和新闻id查询当前用户是否收藏当前新闻
    order = select(Favorite).where(Favorite.user_id == user_id,Favorite.news_id == news_id)
    result = await session.execute(order)
    #能查询到返回True说明新闻被收藏
    return result.scalar_one_or_none() is not None

#添加新闻到收藏状态
async def add_news_favorite(
        session:AsyncSession,
        user_id: int,
        news_id: int,
):
    favorite = Favorite(user_id = user_id,news_id = news_id)
    session.add(favorite)
    await session.commit()
    await session.refresh(favorite)
    return favorite


#移除新闻的收藏状态
async def remove_news_favorite(
        session:AsyncSession,
        user_id: int,
        news_id: int
):
    order = delete(Favorite).where(Favorite.user_id == user_id,Favorite.news_id == news_id)
    res = await session.execute(order)
    await session.commit()
    return res.rowcount > 0

#获取收藏列表
async def get_favorite_list(
        session:AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
):
    count_order = select(func.count()).where(Favorite.user_id == user_id)
    content_result = await session.execute(count_order)
    total = content_result.scalar_one()
    #得到列表
    # [
    #     (新闻对象，收藏时间，收藏id)
    # ]
    order = (select(News,Favorite.created_at.label('favorite_time'),Favorite.id.label('favorite_id'))
             .join(Favorite,News.id == Favorite.news_id)
             .where(Favorite.user_id == user_id)
             .order_by(Favorite.created_at.desc())
             .offset((page-1) * page_size).limit(page_size))
    result = await session.execute(order)
    rows = result.all()
    return rows, total

#清空收藏列表
async def remove_all_favorite(
        session:AsyncSession,
        user_id: int,
):
    order = delete(Favorite).where(Favorite.user_id == user_id)
    result = await session.execute(order)
    await session.commit()

    return result.rowcount or 0