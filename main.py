# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : main.py
# @Desc      : 
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

from fastapi import FastAPI

from core.LoggerDetector import logger
from core.ResponseUtil import ResponseUtil

app = FastAPI()


@app.get("/")
async def health_check():
    message = "服务正在运行中·······"
    logger.info(f"检查服务运行状态: {message}")
    return ResponseUtil.success(message=message)

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)