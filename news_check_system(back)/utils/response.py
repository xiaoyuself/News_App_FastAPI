from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder



#格式化响应通用模板
def success_response(message: str = "success", data=None):
    content = {
        "code": 200,
        "message": message,
        "data": data
    }
    #将content以json形式返回（data里面的数据格式不确定，所以要加这个）
    return JSONResponse(content=jsonable_encoder(content))

