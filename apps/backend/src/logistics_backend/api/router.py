from fastapi import APIRouter
from logistics_backend.api.master_data import router as master_data_router
from logistics_backend.api.jobs import router as jobs_router

router = APIRouter()
router.include_router(master_data_router)
router.include_router(jobs_router)
