"""Delivery-only, one-depot routing probe; all six orders are mandatory."""
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def scenario():
    positions = [(0, 0), (2, 1), (3, 2), (4, 1), (-2, 1), (-3, 2), (-4, 1)]
    return dict(
        matrix=[[abs(a[0]-b[0])+abs(a[1]-b[1]) for b in positions] for a in positions],
        windows=[[0, 40], [0, 15], [5, 22], [8, 30], [0, 15], [5, 22], [8, 30]],
        demands=[0, 2, 2, 2, 2, 2, 2], service=[0, 1, 1, 1, 1, 1, 1],
        temperatures=[None, 'chilled', 'chilled', 'chilled', 'frozen', 'frozen', 'frozen'],
        vehicles=[dict(capacity=6, temperature='chilled'), dict(capacity=6, temperature='frozen')],
    )


def solve(data):
    manager = pywrapcp.RoutingIndexManager(len(data['matrix']), len(data['vehicles']), 0)
    routing = pywrapcp.RoutingModel(manager)

    def transit(a, b):
        a, b = manager.IndexToNode(a), manager.IndexToNode(b)
        return data['matrix'][a][b] + data['service'][a]

    callback = routing.RegisterTransitCallback(transit)
    routing.SetArcCostEvaluatorOfAllVehicles(callback)
    horizon = data['windows'][0][1]
    routing.AddDimension(callback, horizon, horizon, False, 'time')
    time = routing.GetDimensionOrDie('time')
    demand = routing.RegisterUnaryTransitCallback(lambda i: data['demands'][manager.IndexToNode(i)])
    routing.AddDimensionWithVehicleCapacity(demand, 0, [v['capacity'] for v in data['vehicles']], True, 'load')
    for node in range(1, len(data['matrix'])):
        index = manager.NodeToIndex(node)
        time.CumulVar(index).SetRange(*data['windows'][node])
        allowed = [i for i, v in enumerate(data['vehicles']) if v['temperature'] == data['temperatures'][node]]
        if not allowed:
            return dict(status='INFEASIBLE_INPUT', reason=f'no_compatible_vehicle:{node}', routes=[])
        # Remove incompatible values individually: avoids the 9.15 Windows Span binding.
        for vehicle in range(len(data['vehicles'])):
            if vehicle not in allowed:
                routing.VehicleVar(index).RemoveValue(vehicle)
        routing.AddVariableMinimizedByFinalizer(time.CumulVar(index))
    for vehicle in range(len(data['vehicles'])):
        for index in (routing.Start(vehicle), routing.End(vehicle)):
            time.CumulVar(index).SetRange(*data['windows'][0])
            routing.AddVariableMinimizedByFinalizer(time.CumulVar(index))
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.time_limit.seconds = 2
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return dict(status='NO_SOLUTION_FOUND', solver_status=routing.status(), routes=[])
    routes = []
    for vehicle in range(len(data['vehicles'])):
        index, stops = routing.Start(vehicle), []
        while True:
            stops.append(dict(node=manager.IndexToNode(index), time=solution.Value(time.CumulVar(index))))
            if routing.IsEnd(index):
                break
            index = solution.Value(routing.NextVar(index))
        routes.append(dict(vehicle=vehicle, stops=stops))
    return dict(status='FEASIBLE', objective=solution.ObjectiveValue(), routes=routes)
