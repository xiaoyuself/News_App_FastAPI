from urllib.error import HTTPError

from fastapi import FastAPI, APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_session
from crud import favorite
from crud.favorite import is_news_favorite, add_news_favorite, remove_news_favorite, remove_all_favorite
from models.users import User
from schemas.favorite import FavoriteCheckResponse, FavoriteAddRequest, FavoriteListRequest
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/favorite", tags=["favorite"])

#获取新闻收藏状态路由
@router.get("/check")
async def check_favorite(
        news_id:int=Query(...,alias='newId'),
        user:User=Depends(get_current_user),
        session:AsyncSession = Depends(get_session)
):
    #is_favorite为True或者False
    is_favorite= await is_news_favorite(session,news_id=news_id,user_id=user.id)
    return success_response(message='检查收藏状态成功',data=FavoriteCheckResponse(isFavorite=is_favorite))

#添加新闻到收藏路由
@router.post('/add')
async def add_favorite(
        data:FavoriteAddRequest,
        user:User=Depends(get_current_user),
        session:AsyncSession = Depends(get_session)
):
    result = await add_news_favorite(session,user.id,data.news_id)
    return success_response(message='添加收藏成功',data = result)


#清除新闻收藏状态路由
@router.delete('/remove')
async def remove_favorite(
        user:User=Depends(get_current_user),
        session:AsyncSession = Depends(get_session),
        news_id:int=Query(...,alias='newsId')
):
    result = await remove_news_favorite(session,user.id,news_id)
    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,detail = '删除失败')
    return success_response(message='删除成功')


#获取收藏列表
@router.get('/list')
async def get_favorite_list(
        page:int = Query(default=1,ge=1),
        page_size:int = Query(default=10,ge=1,le=100,alias='pageSize'),
        user:User=Depends(get_current_user),
        session:AsyncSession = Depends(get_session)
):
    rows,total = await favorite.get_favorite_list(session,user.id,page,page_size)
    favorite_list = [
        {
            **news.__dict__,
            'favorite_time':favorite_time,
            'favorite_id':favorite_id
        } for news,favorite_time,favorite_id in rows
    ]
    has_more = total > page * page_size

    data = FavoriteListRequest(list = favorite_list,total=total,hasMore=has_more)
    return success_response(message='收藏列表获取成功',data=data)


#清空收藏列表
@router.delete('/clear')
async def clear_favorite(
        user:User=Depends(get_current_user),
        session:AsyncSession = Depends(get_session)
):
    count = await remove_all_favorite(session,user.id)
    return success_response(message=f'删除成功{count}条数据')