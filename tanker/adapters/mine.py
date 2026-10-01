"""Best-improvement relocation search, initialized by the starter solver."""

import random
import time

from adapter import Solver, route_load, total_length
from adapters.baseline import BaselineSolver, two_opt
from adapters.starter import StarterSolver
from data import distance_matrix


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


def best_segment_relocate_once(d, instance, routes, loads):
    """Move the best capacity-feasible contiguous segment of up to five villages."""
    best_delta = 0
    best_move = None

    for source_index, source_route in enumerate(routes):
        for segment_size in range(1, min(5, len(source_route)) + 1):
            for start in range(len(source_route) - segment_size + 1):
                segment = source_route[start:start + segment_size]
                segment_load = sum(instance.demand[v] for v in segment)
                if segment_load > instance.capacity:
                    continue
                previous = source_route[start - 1] if start else 0
                following = source_route[start + segment_size] if start + segment_size < len(source_route) else 0
                removal_delta = d[previous][following] - d[previous][segment[0]] - d[segment[-1]][following]
                remaining_route = source_route[:start] + source_route[start + segment_size:]

                for insert_at in range(len(remaining_route) + 1):
                    if insert_at == start:
                        continue
                    left = remaining_route[insert_at - 1] if insert_at else 0
                    right = remaining_route[insert_at] if insert_at < len(remaining_route) else 0
                    delta = removal_delta + d[left][segment[0]] + d[segment[-1]][right] - d[left][right]
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (source_index, start, segment_size, source_index, insert_at, segment_load)

                for target_index, target_route in enumerate(routes):
                    if target_index == source_index or loads[target_index] + segment_load > instance.capacity:
                        continue
                    for insert_at in range(len(target_route) + 1):
                        left = target_route[insert_at - 1] if insert_at else 0
                        right = target_route[insert_at] if insert_at < len(target_route) else 0
                        insertion_delta = d[left][segment[0]] + d[segment[-1]][right] - d[left][right]
                        delta = removal_delta + insertion_delta
                        if delta < best_delta:
                            best_delta = delta
                            best_move = (source_index, start, segment_size, target_index, insert_at, segment_load)

    if best_move is None:
        return None

    source_index, start, segment_size, target_index, insert_at, segment_load = best_move
    segment = routes[source_index][start:start + segment_size]
    del routes[source_index][start:start + segment_size]
    routes[target_index][insert_at:insert_at] = segment
    if target_index != source_index:
        loads[source_index] -= segment_load
        loads[target_index] += segment_load
    return source_index, target_index


def best_swap_once(d, instance, routes, loads):
    """Swap two villages across routes when the swap reduces distance and fits."""
    best_delta = 0
    best_move = None

    for first_route_index, first_route in enumerate(routes):
        for second_route_index in range(first_route_index + 1, len(routes)):
            second_route = routes[second_route_index]
            for first_position, first_village in enumerate(first_route):
                first_previous = first_route[first_position - 1] if first_position else 0
                first_following = first_route[first_position + 1] if first_position + 1 < len(first_route) else 0
                for second_position, second_village in enumerate(second_route):
                    first_load = loads[first_route_index] - instance.demand[first_village] + instance.demand[second_village]
                    if first_load > instance.capacity:
                        continue
                    second_load = loads[second_route_index] - instance.demand[second_village] + instance.demand[first_village]
                    if second_load > instance.capacity:
                        continue

                    second_previous = second_route[second_position - 1] if second_position else 0
                    second_following = second_route[second_position + 1] if second_position + 1 < len(second_route) else 0
                    delta = (
                        d[first_previous][second_village] + d[second_village][first_following]
                        - d[first_previous][first_village] - d[first_village][first_following]
                        + d[second_previous][first_village] + d[first_village][second_following]
                        - d[second_previous][second_village] - d[second_village][second_following]
                    )
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (first_route_index, first_position, second_route_index, second_position)

    if best_move is None:
        return None

    first_route_index, first_position, second_route_index, second_position = best_move
    first_village = routes[first_route_index][first_position]
    second_village = routes[second_route_index][second_position]
    routes[first_route_index][first_position] = second_village
    routes[second_route_index][second_position] = first_village
    loads[first_route_index] += instance.demand[second_village] - instance.demand[first_village]
    loads[second_route_index] += instance.demand[first_village] - instance.demand[second_village]
    return first_route_index, second_route_index


def best_tail_exchange_once(d, instance, routes, loads):
    """Exchange route tails at the best capacity-feasible pair of cut points."""
    best_delta = 0
    best_move = None

    for first_route_index, first_route in enumerate(routes):
        first_prefix = [0]
        for village in first_route:
            first_prefix.append(first_prefix[-1] + instance.demand[village])

        for second_route_index in range(first_route_index + 1, len(routes)):
            second_route = routes[second_route_index]
            second_prefix = [0]
            for village in second_route:
                second_prefix.append(second_prefix[-1] + instance.demand[village])

            for first_cut in range(len(first_route) + 1):
                first_prefix_load = first_prefix[first_cut]
                first_previous = first_route[first_cut - 1] if first_cut else 0
                first_suffix_start = first_route[first_cut] if first_cut < len(first_route) else 0
                for second_cut in range(len(second_route) + 1):
                    new_first_load = first_prefix_load + loads[second_route_index] - second_prefix[second_cut]
                    if new_first_load > instance.capacity:
                        continue
                    new_second_load = second_prefix[second_cut] + loads[first_route_index] - first_prefix_load
                    if new_second_load > instance.capacity:
                        continue

                    second_previous = second_route[second_cut - 1] if second_cut else 0
                    second_suffix_start = second_route[second_cut] if second_cut < len(second_route) else 0
                    delta = (
                        d[first_previous][second_suffix_start] + d[second_previous][first_suffix_start]
                        - d[first_previous][first_suffix_start] - d[second_previous][second_suffix_start]
                    )
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (first_route_index, first_cut, second_route_index, second_cut,
                                     new_first_load, new_second_load)

    if best_move is None:
        return None

    first_route_index, first_cut, second_route_index, second_cut, first_load, second_load = best_move
    first_tail = routes[first_route_index][first_cut:]
    second_tail = routes[second_route_index][second_cut:]
    routes[first_route_index][first_cut:] = second_tail
    routes[second_route_index][second_cut:] = first_tail
    loads[first_route_index] = first_load
    loads[second_route_index] = second_load
    return first_route_index, second_route_index


def randomized_routes(instance, d, rng):
    """Build a feasible nearest-neighbour plan with randomized candidate choice."""
    unvisited = set(range(1, instance.size + 1))
    routes = []
    top_k = rng.randint(2, 8)

    while unvisited:
        route = []
        load = 0
        position = 0
        while True:
            fits = [v for v in unvisited if load + instance.demand[v] <= instance.capacity]
            if not fits:
                break
            fits.sort(key=lambda v: (d[position][v], v))
            village = rng.choice(fits[:top_k])
            route.append(village)
            load += instance.demand[village]
            position = village
            unvisited.remove(village)
        if not route:
            return None
        routes.append(route)
        if len(routes) > instance.fleet:
            return None

    return routes


def perturb_routes(instance, d, routes, rng):
    """Ruin and greedily rebuild a subset of a feasible incumbent plan."""
    candidate = [route[:] for route in routes]
    if not any(candidate):
        return None

    village_count = sum(map(len, candidate))
    remove_count = max(2, int(village_count * rng.uniform(0.12, 0.28)))
    selected = []
    for route_index, route in enumerate(candidate):
        for position, village in enumerate(route):
            selected.append((rng.random(), route_index, village))
    removed = [(route_index, village) for _, route_index, village in sorted(selected)[:remove_count]]
    for route_index, village in removed:
        candidate[route_index].remove(village)

    loads = [route_load(instance, route) for route in candidate]
    pending = [village for _, village in removed]
    pending.sort(key=lambda village: (-instance.demand[village], village))
    for village in pending:
        best_delta = None
        best_position = None
        for route_index, route in enumerate(candidate):
            if loads[route_index] + instance.demand[village] > instance.capacity:
                continue
            for position in range(len(route) + 1):
                left = route[position - 1] if position else 0
                right = route[position] if position < len(route) else 0
                delta = d[left][village] + d[village][right] - d[left][right]
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_position = (route_index, position)

        if best_position is None:
            return None
        route_index, position = best_position
        candidate[route_index].insert(position, village)
        loads[route_index] += instance.demand[village]

    return candidate


def improve_routes(d, instance, routes, deadline):
    """Descend through improving relocations, swaps, tail exchanges and 2-opt."""
    for route in routes:
        if time.monotonic() >= deadline:
            return routes
        two_opt(d, route)

    loads = [route_load(instance, route) for route in routes]
    while time.monotonic() < deadline:
        changed_routes = best_relocate_once(d, instance, routes, loads)
        if changed_routes is None:
            changed_routes = best_segment_relocate_once(d, instance, routes, loads)
        if changed_routes is None:
            changed_routes = best_swap_once(d, instance, routes, loads)
        if changed_routes is None:
            changed_routes = best_tail_exchange_once(d, instance, routes, loads)
        if changed_routes is None:
            break
        for route_index in changed_routes:
            two_opt(d, routes[route_index])
    return routes


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
                changed_routes = best_segment_relocate_once(d, instance, routes, loads)
            if changed_routes is None:
                changed_routes = best_swap_once(d, instance, routes, loads)
            if changed_routes is None:
                changed_routes = best_tail_exchange_once(d, instance, routes, loads)
            if changed_routes is None:
                break
            for route_index in changed_routes:
                two_opt(d, routes[route_index])
            receipt = submit_candidate({"routes": routes})

        best_routes = [route[:] for route in routes]
        best_cost = total_length(instance, best_routes)
        receipts = [receipt]

        def submit_baseline_candidate(candidate):
            nonlocal best_routes, best_cost
            candidate_routes = candidate["routes"]
            candidate_cost = total_length(instance, candidate_routes)
            if candidate_cost < best_cost:
                best_cost = candidate_cost
                best_routes = [route[:] for route in candidate_routes]
            receipts[0] = submit_candidate({"routes": best_routes})
            return receipts[0]

        BaselineSolver().solve(instance, submit_baseline_candidate)

        rng = random.Random(int(instance.digest, 16))
        while receipts[0]["remaining_s"] > SAFETY_S:
            if rng.random() < 0.65:
                candidate_routes = perturb_routes(instance, d, best_routes, rng)
            else:
                candidate_routes = randomized_routes(instance, d, rng)
            if candidate_routes is not None:
                deadline = time.monotonic() + receipts[0]["remaining_s"] - SAFETY_S
                improve_routes(d, instance, candidate_routes, deadline)
                candidate_cost = total_length(instance, candidate_routes)
                if candidate_cost < best_cost:
                    best_cost = candidate_cost
                    best_routes = [route[:] for route in candidate_routes]
            receipts[0] = submit_candidate({"routes": best_routes})

        return {"routes": [route for route in best_routes if route]}