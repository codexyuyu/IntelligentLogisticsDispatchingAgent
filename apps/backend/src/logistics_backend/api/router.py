from fastapi import APIRouter
from logistics_backend.api.agents import router as agents_router
from logistics_backend.api.master_data import router as master_data_router
from logistics_backend.api.metrics import router as metrics_router
from logistics_backend.api.events import router as events_router
from logistics_backend.api.exceptions import router as exceptions_router
from logistics_backend.api.impact import router as impact_router
from logistics_backend.api.jobs import router as jobs_router
from logistics_backend.api.optimization import router as optimization_router
from logistics_backend.api.reschedule import router as reschedule_router
from logistics_backend.api.results import router as results_router
from logistics_backend.api.simulations import router as simulations_router
from logistics_backend.api.validation import router as validation_router
from logistics_backend.api.warehouse import router as warehouse_router
from logistics_backend.api.workbench import router as workbench_router

router = APIRouter()
router.include_router(master_data_router)
router.include_router(jobs_router)
router.include_router(events_router)
router.include_router(exceptions_router)
router.include_router(impact_router)
router.include_router(metrics_router)
router.include_router(agents_router)
router.include_router(optimization_router)
router.include_router(warehouse_router)
router.include_router(simulations_router)
router.include_router(results_router)
router.include_router(validation_router)
router.include_router(reschedule_router)
router.include_router(workbench_router)
