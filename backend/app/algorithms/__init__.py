from .astar import astar
from .bfs import bfs
from .greedy_best_first import greedy_best_first
from .graph import Edge, Graph, SearchResult, edge_id, edge_key

ALGORITHMS = {"astar": astar, "bfs": bfs, "greedy": greedy_best_first}
ALGORITHM_LABELS = {"astar": "A* Search", "bfs": "Breadth-First Search", "greedy": "Greedy Best-First"}

__all__ = ["astar", "bfs", "greedy_best_first", "Edge", "Graph", "SearchResult",
           "edge_id", "edge_key", "ALGORITHMS", "ALGORITHM_LABELS"]
