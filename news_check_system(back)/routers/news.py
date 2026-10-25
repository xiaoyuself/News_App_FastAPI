from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_session
from crud.news import get_Categories, get_news_list, get_news_count, get_news_detail, increase_view_count, \
    get_related_news

news_router = APIRouter(prefix='/api/news',tags=['news'])

#获取新闻分类路由
@news_router.get('/categories')
async def categories(db:AsyncSession = Depends(get_session),skip:int=0,limit:int=100):
    #获取新闻分类信息
    categories = await get_Categories(db,skip,limit)
    #返回数据
    return {
        'code':200,
        'message':'sucess',
        'data':categories
    }

#获取新闻列表路由
@news_router.get('/list')
async def news_list(
        db:AsyncSession = Depends(get_session),
        category_id:int = Query(...,alias='categoryId'),
        page:int = 1,
        page_size:int=Query(10,alias='pageSize',le=100)
):
    #根据页数和每页的数量设置skip
    skip = (page-1)*page_size
    news_list = await get_news_list(db,category_id,skip,page_size)
    total = await get_news_count(db,category_id)
    #如果当前展示新闻数量小于总数说明还有新闻，传给前端让其控制下拉
    more = (skip+len(news_list)) < total

    return{
        'code':200,
        'message':'获取新闻列表成功',
        'data':{
            'list':news_list,
            'total':total,
            'hasMore':more,
        }
    }


#获取新闻详情路由
@news_router.get('/detail')
async def news_detail(
        news_id:int=Query(...,alias='id'),
        session:AsyncSession = Depends(get_session),
):
    #根据点击的新闻id获取新闻详情
    news_detail = await get_news_detail(session,news_id)
    if not news_detail:
        raise HTTPException(status_code=404,detail = '新闻不存在')
    #点击后需要将新闻浏览量+1
    res = await increase_view_count(session,news_id)
    if not res:
        raise HTTPException(status_code=404,detail = '新闻不存在')
    #还要根据新闻分类获取当前新闻种类中浏览量最高的5条新闻作为推荐返回
    relatedNews = await get_related_news(session,news_id,news_detail.category_id)


    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": news_detail.id,
            "title": news_detail.title,
            "content": news_detail.content,
            "image": news_detail.image,
            "author": news_detail.author,
            "publishTime": news_detail.publish_time,
            "categoryId": news_detail.category_id,
            "views": news_detail.views,
            "relatedNews": relatedNews
        }
    }