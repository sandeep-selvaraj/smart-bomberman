from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder


def get_path(mapdata: list, player_node: tuple, enemy_node: tuple) -> list:
    grid = Grid(matrix=_encode_map(mapdata))
    finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
    player_node_x, player_node_y = player_node
    enemy_node_x, enemy_node_y = enemy_node
    player_on_grid = grid.node(player_node_x, player_node_y)
    enemy_on_grid = grid.node(enemy_node_x, enemy_node_y)
    path, runs = finder.find_path(player_on_grid, enemy_on_grid, grid)
    return path


def _encode_map(mapdata: list) -> list:
    """Encode cells in map to a numerical value."""
    encoded_map = []
    for row_index, row in enumerate(mapdata):
        encoded_column = []
        for column_index, column in enumerate(row):
            if column in ('W', '#', 'B'):
                encoded_column.append(0)
            else:
                encoded_column.append(1)
        encoded_map.append(encoded_column)
    return encoded_map
