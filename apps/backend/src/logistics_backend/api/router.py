from fastapi import APIRouter
from logistics_backend.api.master_data import router as master_data_router
from logistics_backend.api.events import router as events_router
from logistics_backend.api.jobs import router as jobs_router
from logistics_backend.api.optimization import router as optimization_router
from logistics_backend.api.results import router as results_router
from logistics_backend.api.simulations import router as simulations_router
from logistics_backend.api.warehouse import router as warehouse_router

router = APIRouter()
router.include_router(master_data_router)
router.include_router(jobs_router)
router.include_router(events_router)
router.include_router(optimization_router)
router.include_router(warehouse_router)
router.include_router(simulations_router)
router.include_router(results_router)
