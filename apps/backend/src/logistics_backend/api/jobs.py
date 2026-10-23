from uuid import UUID
from fastapi import APIRouter, Depends
from logistics_contracts.runtime import JobView, CancelCommand
from logistics_backend.api.dependencies import actor, operator, job_service

router = APIRouter(tags=["jobs"])

@router.get("/jobs/{job_id}", response_model=JobView, operation_id="get_job")
def get_job(job_id: UUID, current=Depends(actor), service=Depends(job_service)):
    return service.get(job_id, current)

@router.post("/jobs/{job_id}/cancel", response_model=JobView, operation_id="cancel_job")
def cancel_job(job_id: UUID, command: CancelCommand, current=Depends(operator), service=Depends(job_service)):
    return service.cancel(job_id, command, current)
