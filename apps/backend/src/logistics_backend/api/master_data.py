"""Master-data HTTP routes; business writes are delegated to the service."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from logistics_contracts import http, entities, planning
from logistics_backend.api.dependencies import actor, operator, revision, master_service
from logistics_backend.errors import ServiceError
from logistics_domain.states import ErrorCode

router = APIRouter(tags=["master-data"])

@router.get("/matrices", response_model=tuple[planning.TravelMatrixDTO, ...],
            operation_id="list_travel_matrices")
def list_travel_matrices(request: Request, current=Depends(actor)):
    return request.app.state.snapshots.list_matrices()

@router.get("/orders", response_model=http.OrderPage, operation_id="list_orders")
def list_orders(query: http.OrderFilter = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("order", query, current)

@router.post("/orders", response_model=entities.OrderDTO, status_code=201, operation_id="create_order")
def create_order(command: http.OrderCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("order", command, current)

@router.get("/orders/{entity_id}", response_model=entities.OrderDTO, operation_id="get_order")
def get_order(entity_id: UUID, current=Depends(actor), service=Depends(master_service)):
    return service.get("order", entity_id, current)

@router.patch("/orders/{entity_id}", response_model=entities.OrderDTO, operation_id="update_order")
def update_order(entity_id: UUID, command: http.OrderUpdate, expected=Depends(revision), current=Depends(operator), service=Depends(master_service)):
    return service.update("order", entity_id, command, expected, current)

@router.get("/vehicles", response_model=http.VehiclePage, operation_id="list_vehicles")
def list_vehicles(query: http.VehicleFilter = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("vehicle", query, current)

@router.post("/vehicles", response_model=entities.VehicleDTO, status_code=201, operation_id="create_vehicle")
def create_vehicle(command: http.VehicleCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("vehicle", command, current)

@router.get("/vehicles/{entity_id}", response_model=entities.VehicleDTO, operation_id="get_vehicle")
def get_vehicle(entity_id: UUID, current=Depends(actor), service=Depends(master_service)):
    return service.get("vehicle", entity_id, current)

@router.patch("/vehicles/{entity_id}", response_model=entities.VehicleDTO, operation_id="update_vehicle")
def update_vehicle(entity_id: UUID, command: http.VehicleUpdate, expected=Depends(revision), current=Depends(operator), service=Depends(master_service)):
    return service.update("vehicle", entity_id, command, expected, current)

@router.get("/drivers", response_model=http.DriverPage, operation_id="list_drivers")
def list_drivers(query: http.DriverQuery = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("driver", query, current)

@router.post("/drivers", response_model=entities.DriverDTO, status_code=201, operation_id="create_driver")
def create_driver(command: http.DriverCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("driver", command, current)

@router.get("/drivers/{entity_id}", response_model=entities.DriverDTO, operation_id="get_driver")
def get_driver(entity_id: UUID, current=Depends(actor), service=Depends(master_service)):
    return service.get("driver", entity_id, current)

@router.patch("/drivers/{entity_id}", response_model=entities.DriverDTO, operation_id="update_driver")
def update_driver(entity_id: UUID, command: http.DriverUpdate, expected=Depends(revision), current=Depends(operator), service=Depends(master_service)):
    return service.update("driver", entity_id, command, expected, current)

@router.get("/warehouses", response_model=http.WarehousePage, operation_id="list_warehouses")
def list_warehouses(query: http.WarehouseFilter = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("warehouse", query, current)

@router.post("/warehouses", response_model=entities.WarehouseDTO, status_code=201, operation_id="create_warehouse")
def create_warehouse(command: http.WarehouseCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("warehouse", command, current)

@router.get("/warehouses/{entity_id}", response_model=entities.WarehouseDTO, operation_id="get_warehouse")
def get_warehouse(entity_id: UUID, current=Depends(actor), service=Depends(master_service)):
    return service.get("warehouse", entity_id, current)

@router.patch("/warehouses/{entity_id}", response_model=entities.WarehouseDTO, operation_id="update_warehouse")
def update_warehouse(entity_id: UUID, command: http.WarehouseUpdate, expected=Depends(revision), current=Depends(operator), service=Depends(master_service)):
    return service.update("warehouse", entity_id, command, expected, current)

@router.get("/warehouses/{warehouse_id}/zones", response_model=http.ZonePage, operation_id="list_zones")
def list_zones(warehouse_id: UUID, query: http.ZoneQuery = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("zone", query, current, warehouse_id=warehouse_id)

@router.post("/warehouses/{warehouse_id}/zones", response_model=entities.ZoneDTO, status_code=201, operation_id="create_zone")
def create_zone(warehouse_id: UUID, command: http.ZoneCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("zone", command, current, warehouse_id=warehouse_id)

@router.get("/warehouses/{warehouse_id}/locations", response_model=http.LocationPage, operation_id="list_locations")
def list_locations(warehouse_id: UUID, query: http.LocationQuery = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("location", query, current, warehouse_id=warehouse_id)

@router.post("/warehouses/{warehouse_id}/locations", response_model=entities.StorageLocationDTO, status_code=201, operation_id="create_location")
def create_location(warehouse_id: UUID, command: http.LocationCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("location", command, current, warehouse_id=warehouse_id)

@router.get("/warehouses/{warehouse_id}/docks", response_model=http.DockPage, operation_id="list_docks")
def list_docks(warehouse_id: UUID, query: http.DockQuery = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("dock", query, current, warehouse_id=warehouse_id)

@router.post("/warehouses/{warehouse_id}/docks", response_model=entities.DockDTO, status_code=201, operation_id="create_dock")
def create_dock(warehouse_id: UUID, command: http.DockCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("dock", command, current, warehouse_id=warehouse_id)

@router.get("/warehouses/{warehouse_id}/workers", response_model=http.WorkerPage, operation_id="list_workers")
def list_workers(warehouse_id: UUID, query: http.WorkerQuery = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("worker", query, current, warehouse_id=warehouse_id)

@router.post("/warehouses/{warehouse_id}/workers", response_model=entities.WorkerDTO, status_code=201, operation_id="create_worker")
def create_worker(warehouse_id: UUID, command: http.WorkerCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("worker", command, current, warehouse_id=warehouse_id)

@router.get("/warehouses/{warehouse_id}/equipment", response_model=http.EquipmentPage, operation_id="list_equipment")
def list_equipment(warehouse_id: UUID, query: http.EquipmentQuery = Depends(), current=Depends(actor), service=Depends(master_service)):
    return service.list("equipment", query, current, warehouse_id=warehouse_id)

@router.post("/warehouses/{warehouse_id}/equipment", response_model=entities.EquipmentDTO, status_code=201, operation_id="create_equipment")
def create_equipment(warehouse_id: UUID, command: http.EquipmentCreate, current=Depends(operator), service=Depends(master_service)):
    return service.create("equipment", command, current, warehouse_id=warehouse_id)

@router.patch("/resources/{kind}/{entity_id}", response_model=entities.ResourceDTO, operation_id="update_resource")
def update_resource(kind: str, entity_id: UUID, command: http.ResourceUpdate, expected=Depends(revision), current=Depends(operator), service=Depends(master_service)):
    if kind != command.kind:
        raise ServiceError(ErrorCode.INVALID_INPUT, "path kind differs from body")
    return {"kind": kind, "value": service.update(kind, entity_id, command.changes, expected, current)}

@router.get("/resources/{kind}/{entity_id}/calendar", response_model=entities.CalendarDTO, operation_id="get_resource_calendar")
def get_calendar(kind: str, entity_id: UUID, current=Depends(actor), service=Depends(master_service)):
    if kind not in ("location", "dock", "worker", "equipment"):
        raise ServiceError(ErrorCode.INVALID_INPUT, "resource kind has no calendar endpoint")
    return service.get(kind, entity_id, current).calendar

@router.put("/resources/{kind}/{entity_id}/calendar", response_model=entities.CalendarDTO, operation_id="put_resource_calendar")
def put_calendar(kind: str, entity_id: UUID, command: entities.CalendarDTO, expected=Depends(revision), current=Depends(operator), service=Depends(master_service)):
    return service.put_calendar(kind, entity_id, command, expected, current).calendar
