from fastapi import APIRouter
from .datasets import router as datasets_router
from .sessions import router as sessions_router
from .chat import router as chat_router
from .charts import router as charts_router
from .reports import router as reports_router

api_router = APIRouter()
api_router.include_router(datasets_router)
api_router.include_router(sessions_router)
api_router.include_router(chat_router)
api_router.include_router(charts_router)
api_router.include_router(reports_router)
