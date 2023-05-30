"""File handles the implementation of A star algorithm."""
from pathfinding.core.diagonal_movement import DiagonalMovement  # type: ignore
from pathfinding.core.grid import Grid  # type: ignore
from pathfinding.finder.a_star import AStarFinder  # type: ignore


def get_path(mapdata: list, player_node: tuple, enemy_node: tuple) -> list:
    """
    :param mapdata: List of the mapdata
    :param player_node: Player location
    :param enemy_node: Enemy location
    :return: Possible path to enemy
    """
    grid = Grid(matrix=_encode_map(mapdata))
    finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
    player_node_x, player_node_y = player_node
    enemy_node_x, enemy_node_y = enemy_node
    player_on_grid = grid.node(player_node_x, player_node_y)
    enemy_on_grid = grid.node(enemy_node_x, enemy_node_y)
    path, _ = finder.find_path(player_on_grid, enemy_on_grid, grid)
    return path


def _encode_map(mapdata: list) -> list:
    """Encode cells in map to a numerical value."""
    encoded_map = []
    for row in mapdata:
        encoded_column = []
        for column in row:
            if column in ('W', '#', 'B_1', 'B_2'):
                encoded_column.append(0)
            else:
                encoded_column.append(1)
        encoded_map.append(encoded_column)
    return encoded_map
