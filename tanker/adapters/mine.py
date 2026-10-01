"""Best-improvement relocation search, initialized by the starter solver."""

from adapter import Solver, route_load
from adapters.baseline import BaselineSolver, two_opt
from adapters.starter import StarterSolver
from data import distance_matrix
from adapter import total_length


SAFETY_S = 0.2


def best_relocate_once(d, instance, routes, loads):
    """Apply the most cost-saving single-village relocation available."""
    best_delta = 0
    best_move = None

    for source_index, source_route in enumerate(routes):
        for village_index, village in enumerate(source_route):
            previous = source_route[village_index - 1] if village_index else 0
            following = source_route[village_index + 1] if village_index + 1 < len(source_route) else 0
            removal_delta = d[previous][following] - d[previous][village] - d[village][following]

            for target_index, target_route in enumerate(routes):
                if target_index == source_index or loads[target_index] + instance.demand[village] > instance.capacity:
                    continue
                for insert_at in range(len(target_route) + 1):
                    left = target_route[insert_at - 1] if insert_at else 0
                    right = target_route[insert_at] if insert_at < len(target_route) else 0
                    insertion_delta = d[left][village] + d[village][right] - d[left][right]
                    delta = removal_delta + insertion_delta
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (source_index, village_index, target_index, insert_at, village)

    if best_move is None:
        return None

    source_index, village_index, target_index, insert_at, village = best_move
    routes[source_index].pop(village_index)
    routes[target_index].insert(insert_at, village)
    loads[source_index] -= instance.demand[village]
    loads[target_index] += instance.demand[village]
    return source_index, target_index


class MySolver(Solver):
    def solve(self, instance, submit_candidate):
        d = distance_matrix(instance)
        routes = StarterSolver().solve(instance, submit_candidate)["routes"]
        for route in routes:
            two_opt(d, route)
        receipt = submit_candidate({"routes": routes})
        loads = [route_load(instance, route) for route in routes]
        while receipt["remaining_s"] > SAFETY_S:
            changed_routes = best_relocate_once(d, instance, routes, loads)
            if changed_routes is None:
                break
            for route_index in changed_routes:
                two_opt(d, routes[route_index])
            receipt = submit_candidate({"routes": routes})

        best_routes = [route[:] for route in routes]
        best_cost = total_length(instance, best_routes)

        def submit_baseline_candidate(candidate):
            nonlocal best_routes, best_cost
            candidate_routes = candidate["routes"]
            candidate_cost = total_length(instance, candidate_routes)
            if candidate_cost < best_cost:
                best_cost = candidate_cost
                best_routes = [route[:] for route in candidate_routes]
            return submit_candidate({"routes": best_routes})

        BaselineSolver().solve(instance, submit_baseline_candidate)
        return {"routes": [route for route in best_routes if route]}