# -*- coding: utf-8 -*-
import numpy as np
import numba as nb
from typing import Union

from honeybees.library import geohash

@nb.njit(cache=True)
def find_neighbor_search_count_index(search_counts, search_count_index, r):
    for neighbor_search_counts_index in range(search_count_index, -1, -1):
        if r >= search_counts[neighbor_search_counts_index, 2]:
            neighbor_search_counts_index += 1
            break
    return neighbor_search_counts_index

@nb.njit(parallel=True, locals={"r": nb.uint32}, cache=True)
def find_neighbors_numba(
    search_target_unique_hashcodes,
    search_source_unique_hashcodes,
    search_target_hashcodes_sort_indices,
    cumulative_count_per_search_hashcode,
    search_source_cumulative_counts_per_hashcode,
    map_search_source_to_target,
    reverse_search_source_hashcodes_sort_indices,
    n_neighbor,
    radius,
    bits,
    dtype,
    minx,
    maxx,
    miny,
    maxy,
    grid
):
    nanvalue = np.iinfo(dtype).max # use the maximum value of uint as nanvalue
    neighbors = np.full((map_search_source_to_target.size, n_neighbor), nanvalue, dtype=dtype)
    n_unique_hashcodes = search_target_unique_hashcodes.size
    for u in nb.prange(search_source_unique_hashcodes.size):
        search_source_hashcode = search_source_unique_hashcodes[u]
        x, y = geohash.decode(search_source_hashcode, bits, minx=minx, maxx=maxx, miny=miny, maxy=maxy)
        shifts = geohash.get_shifts(x, y, radius, bits, minx, maxx, miny, maxy, grid)
        neighbor_geohashes = geohash.shift_multiple(search_source_hashcode, bits, shifts)
        neighbor_geohashes = np.sort(neighbor_geohashes)
        search_counts = np.zeros((neighbor_geohashes.size, 3), dtype=dtype)

        index = -1
        search_count_index = 0
        previous_neighbor_geohash = 0
        for neighbor_geohash in neighbor_geohashes:
            if neighbor_geohash == previous_neighbor_geohash + 1:
                if index == n_unique_hashcodes:
                    break
                if search_target_unique_hashcodes[index] == neighbor_geohash:
                    search_counts[search_count_index, 1] += (cumulative_count_per_search_hashcode[index+1] - cumulative_count_per_search_hashcode[index])
                    index += 1
            else:
                if search_counts[search_count_index, 1] != 0:
                    search_count_index += 1
                index = np.searchsorted(search_target_unique_hashcodes, neighbor_geohash)
                if index == n_unique_hashcodes:
                    break
                search_counts[search_count_index, 0] = cumulative_count_per_search_hashcode[index]
                if search_target_unique_hashcodes[index] == neighbor_geohash:
                    search_counts[search_count_index, 1] += (cumulative_count_per_search_hashcode[index+1] - cumulative_count_per_search_hashcode[index])
                    index += 1

            if neighbor_geohash == search_source_hashcode:
                self_index = search_count_index
            previous_neighbor_geohash = neighbor_geohash

        if search_counts[search_count_index, 1] == 0:
            search_count_index -= 1
        search_counts = search_counts[:search_count_index+1, :]
        search_counts[:, 2] = np.cumsum(search_counts[:, 1])

        n_neighbors = search_counts[:, 1].sum() - 1  # exclude self (not a neighbor)
        agent_neighbors = np.full(n_neighbor, nanvalue, dtype=dtype)
        if n_neighbors > n_neighbor:
            # To understand the algorithm need to realize that you choose a random value
            # from a range that is smaller than the full range, and then after each value, you extend
            # that to include one more. In the event of a collision, you can safely insert the max because it was never 
            # possible to include it before.

            # The chances of a collision increase at the same rate that the number of values decreases,
            # so the probability of any one number being in the result is not skewed, or biased.
            # from: https://codereview.stackexchange.com/questions/61338/generate-random-numbers-without-repetitions
            for neighbor_index_sorted in range(search_source_cumulative_counts_per_hashcode[u], search_source_cumulative_counts_per_hashcode[u+1]):
                neighbor_index = reverse_search_source_hashcodes_sort_indices[neighbor_index_sorted]
                search_target_agent_index = map_search_source_to_target[neighbor_index_sorted] - search_counts[self_index, 0] + search_counts[:self_index, 1].sum()
                J = n_neighbors - n_neighbor

                if n_neighbor > 20:
                    selected_agents = set()
                
                for i in range(n_neighbor):
                    r = np.random.randint(0, J+1)
                    if r >= search_target_agent_index:  # ensure we do not pick the agent itself and include the last agent
                        r += 1
                    
                    neighbor_search_counts_index = find_neighbor_search_count_index(search_counts, search_count_index, r)
                    if neighbor_search_counts_index == 0:
                        neighbor = search_counts[neighbor_search_counts_index, 0] + r
                    else:
                        neighbor = search_counts[neighbor_search_counts_index, 0] + r - search_counts[neighbor_search_counts_index-1, 2]
                    if n_neighbor > 20:
                        if neighbor in selected_agents:
                            r = int(J)
                            if r >= search_target_agent_index:   # ensure we do not pick the agent itself and include the last agent
                                r += 1
                            neighbor_search_counts_index = find_neighbor_search_count_index(search_counts, search_count_index, r)
                            if neighbor_search_counts_index == 0:
                                neighbor = search_counts[neighbor_search_counts_index, 0] + r
                            else:
                                neighbor = search_counts[neighbor_search_counts_index, 0] + r - search_counts[neighbor_search_counts_index-1, 2]
                        selected_agents.add(neighbor)
                    else:   
                        for k in range(i):
                            if agent_neighbors[k] == neighbor:
                                r = int(J)
                                if r >= search_target_agent_index:   # ensure we do not pick the agent itself and include the last agent
                                    r += 1
                                neighbor_search_counts_index = find_neighbor_search_count_index(search_counts, search_count_index, r)
                                if neighbor_search_counts_index == 0:
                                    neighbor = search_counts[neighbor_search_counts_index, 0] + r
                                else:
                                    neighbor = search_counts[neighbor_search_counts_index, 0] + r - search_counts[neighbor_search_counts_index-1, 2]
                                break                            
                    agent_neighbors[i] = neighbor

                    J += 1
                for f in range(agent_neighbors.size):
                    if agent_neighbors[f] != nanvalue:
                        neighbors[neighbor_index, f] = search_target_hashcodes_sort_indices[agent_neighbors[f]]
                agent_neighbors.fill(nanvalue)
        else:
            for neighbor_index_sorted in range(search_source_cumulative_counts_per_hashcode[u], search_source_cumulative_counts_per_hashcode[u+1]):
                neighbor_index = reverse_search_source_hashcodes_sort_indices[neighbor_index_sorted]
                search_target_agent_index = map_search_source_to_target[neighbor_index_sorted]
                n = 0
                for m in range(search_counts.shape[0]):
                    for o in range(search_counts[m, 1]):
                        neighbor = search_counts[m, 0] + o
                        if neighbor != search_target_agent_index:
                            agent_neighbors[n] = neighbor
                            n += 1
                for f in range(agent_neighbors.size):
                    if agent_neighbors[f] != nanvalue:
                        neighbors[neighbor_index, f] = search_target_hashcodes_sort_indices[agent_neighbors[f]]
                agent_neighbors.fill(nanvalue)
    return neighbors

def process_hashcodes(
    location_hashcodes: np.ndarray,
    search_ids: Union[np.ndarray, None],
    search_target_ids: Union[np.ndarray, None],
    dtype: type
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Args:
        location_hashcodes: Geohashes of all agents.
        search_ids: Ids of the agents to find neighbors for. If None, search all agents.
        dtype: Datatype to use to hold indices.

    Returns:
        search_target_unique_hashcodes: Array of unique geohashes of agents.
        search_source_unique_hashcodes: Array of unique geohashes of agents to find neighbors for.
        search_target_hashcodes_sort_indices: Indices that can be used to sort the `location_hashcodes`.
        cumulative_count_per_search_hashcode: Cumulative count of the unique search hashcodes.
        map_search_source_to_target: 
        search_source_hashcodes_sort_indices: Indices that can be used to sort the `location_hashcodes`.
    """
    if search_ids is None:
        search_ids = np.arange(location_hashcodes.size, dtype=np.int64)
    if search_target_ids is None:
        search_target_ids = np.arange(location_hashcodes.size, dtype=np.int64)
    
    assert isinstance(search_ids, np.ndarray)
    assert isinstance(search_target_ids, np.ndarray)
    
    search_target_hashcodes = location_hashcodes[search_target_ids]
    search_target_hashcodes_sort_indices = np.argsort(search_target_hashcodes).astype(dtype)
    sorted_search_target_hashcodes = search_target_hashcodes[search_target_hashcodes_sort_indices]
    search_target_unique_hashcodes, search_target_unique_index = np.unique(sorted_search_target_hashcodes, return_index=True)
    search_target_unique_index = search_target_unique_index.astype(dtype)
    cumulative_count_per_search_target_hashcode = np.append(search_target_unique_index, sorted_search_target_hashcodes.size)

    # search_target_hashcodes_sort_indices = np.argsort(location_hashcodes).astype(dtype)
    # sorted_search_hashcodes = location_hashcodes[search_target_hashcodes_sort_indices]
    # search_target_unique_hashcodes, search_unique_index = np.unique(sorted_search_hashcodes, return_index=True)
    # search_unique_index = search_unique_index.astype(dtype)
    # cumulative_count_per_search_hashcode = np.append(search_unique_index, sorted_search_hashcodes.size)

    search_source_hashcodes = location_hashcodes[search_ids]
    search_source_hashcodes_sort_indices = np.argsort(search_source_hashcodes).astype(dtype)
    search_source_ids_sorted_by_hashcode = search_ids[search_source_hashcodes_sort_indices]
    search_source_sorted_hashcodes = search_source_hashcodes[search_source_hashcodes_sort_indices]
    search_source_unique_hashcodes, search_source_unique_index = np.unique(search_source_sorted_hashcodes, return_index=True)
    search_source_unique_index = search_source_unique_index.astype(dtype)
    search_source_cumulative_counts_per_hashcode = np.append(search_source_unique_index, search_source_sorted_hashcodes.size)

    inverse_idx = np.empty_like(location_hashcodes)  # should be good, we are mapping targets to sources
    inverse_idx[np.argsort(location_hashcodes).astype(dtype)] = np.arange(0, inverse_idx.size)
    inverse_idx[~np.isin(inverse_idx, search_target_ids)] = -1
    map_search_source_to_target = inverse_idx[search_source_ids_sorted_by_hashcode]
    
    # inverse_idx = np.empty_like(search_target_hashcodes_sort_indices)
    # inverse_idx[search_target_hashcodes_sort_indices] = np.arange(0, inverse_idx.size)
    # map_search_source_to_target = inverse_idx[search_ids_sorted_by_hashcode]

    return (
        search_target_unique_hashcodes,
        search_source_unique_hashcodes,
        search_target_hashcodes_sort_indices,
        cumulative_count_per_search_target_hashcode,
        search_source_cumulative_counts_per_hashcode,
        map_search_source_to_target,
        search_source_hashcodes_sort_indices
    )

def find_neighbors(
    locations: np.ndarray,
    radius: Union[float, int],
    n_neighbor: int,
    bits: int,
    minx: Union[float, int] =-180,
    maxx: Union[float, int]=180,
    miny: Union[float, int]=-90,
    maxy: Union[float, int]=90,
    grid: str='longlat',
    search_ids: Union[None, np.ndarray]=None,
    search_target_ids: Union[np.ndarray, None]=None,
) -> np.ndarray:
    """Finds neighbouring agents for given agents.

    Args:
        locations: Either a 2-dimensional array of x and y locations for agents, or a 1-dimensional array of geohashes.
        radius: Search radius. Specified in meters for grid=longlat, specified in map units for orthogonal grids.
        n_neighbors: Maxiumum number of neighbors to find for each agent.
        bits: Number of bits to use for geohashes.
        minx: Minimum x-value of the entire relevant space.
        maxx: Maximum x-value of the entire relevant space.
        miny: Minimum y-value of the entire relevant space.
        miny: Maximum y-value of the entire relevant space.
        grid: Type of grid. Can be 'longlat' or 'orthogonal'.
        search_ids: Only search for neighbors of agent with search_ids.
        search_target_ids: Only search neighbors with search_target_ids.

    Returns:
        neighbors: 2-dimensional NumPy array. The first dimension represents the results for each of the agents, the second dimension the indices of the neighbors for each of those agents. -1 represents no neighbor (possible only if less than the requested number of neighbors are available in the search radius.)
    """
    assert grid in ('longlat', 'orthogonal')
    if locations.ndim == 2:
        assert locations.shape[1] == 2
        location_hashcodes = geohash.encode_locations(locations, minx, maxx, miny, maxy)
        location_hashcodes = geohash.reduce_precision(location_hashcodes, bits, inplace=True)
    elif locations.ndim == 1:
        location_hashcodes = geohash.reduce_precision(locations, bits, inplace=False)
        assert location_hashcodes.dtype == np.int64
    else:
        raise ValueError("locations must be either 2d-array with lon,lat values or 1d-array of geohashes")

    # test if number of locations is not larger than the maximum value an uint32 can hold. -1 because the max value is used as nan
    if location_hashcodes.size <= np.iinfo(np.uint32).max - 1:
        dtype = np.uint32
    else:
        dtype = np.uint64

    (
        search_target_unique_hashcodes,
        search_source_unique_hashcodes,
        search_target_hashcodes_sort_indices,
        cumulative_count_per_search_hashcode,
        search_source_cumulative_counts_per_hashcode,
        map_search_source_to_target,
        search_source_hashcodes_sort_indices
    ) = process_hashcodes(location_hashcodes, search_ids, search_target_ids, dtype)

    neighbours = find_neighbors_numba(
        search_target_unique_hashcodes=search_target_unique_hashcodes,
        search_source_unique_hashcodes=search_source_unique_hashcodes,
        search_target_hashcodes_sort_indices=search_target_hashcodes_sort_indices,
        cumulative_count_per_search_hashcode=cumulative_count_per_search_hashcode,
        search_source_cumulative_counts_per_hashcode=search_source_cumulative_counts_per_hashcode,
        map_search_source_to_target=map_search_source_to_target,
        reverse_search_source_hashcodes_sort_indices=search_source_hashcodes_sort_indices,
        n_neighbor=n_neighbor,
        radius=radius,
        bits=bits,
        dtype=dtype,
        minx=minx, maxx=maxx, miny=miny, maxy=maxy, grid=grid
    )

    if search_target_ids is not None:
        nanvalue = np.iinfo(dtype).max
        reindex_neighbours = np.take(search_target_ids, neighbours, out=np.empty_like(neighbours), mode='clip')
        reindex_neighbours[neighbours == nanvalue] = nanvalue
        neighbours = reindex_neighbours

    return neighbours

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    n_locations = 1000
    radius = 5000
    n_neighbor = 5
    bits = 29

    locations = np.c_[np.random.uniform(33, 34, n_locations), np.random.uniform(-6, -5, n_locations)]
    search_ids = np.random.choice(np.arange(0, n_locations), 50, replace=False)

    counts = np.zeros(n_locations, dtype=np.int32)
    for i in range(1000):
        neighors = find_neighbors(locations, radius, n_neighbor, bits, search_ids=search_ids)
        for neighbor in neighors.reshape(neighors.size):
            if neighbor != 4294967295:
                counts[neighbor] += 1


    window_width, window_height = geohash.window(bits)

    _, ax = plt.subplots()

    for agent, agent_neighbors in zip(search_ids, neighors):
        agent_neighbors = agent_neighbors[agent_neighbors != 4294967295]
        assert np.unique(agent_neighbors).size == agent_neighbors.size
        geohash_coord = geohash.decode(geohash.encode_precision(*locations[agent], bits), bits)
        shifts = geohash.get_shifts(geohash_coord[0], geohash_coord[1], radius, bits)
        neighbor_geohashes = geohash.shift_multiple(geohash.encode_precision(*locations[agent], bits), bits, shifts)
        neighbor_geohashes = np.sort(neighbor_geohashes)
        for j, neighbor_geohash in enumerate(neighbor_geohashes):
            patch = mpatches.Rectangle(geohash.decode(neighbor_geohash, bits), window_width, window_height, facecolor='orange', edgecolor='black', alpha=j/neighbor_geohashes.size*0.5+0.1)
            ax.add_patch(patch)

        loc = locations[agent]
        for neighbor in agent_neighbors:
            assert agent != neighbor
            neighborloc = locations[neighbor]
            ax.plot([loc[0], neighborloc[0]], [loc[1], neighborloc[1]])

    for x, y, count in zip(locations[:, 0], locations[:, 1], counts):
        ax.annotate(str(count), (x, y))


    ax.scatter(locations[:, 0], locations[:, 1], s=4)
    plt.show()