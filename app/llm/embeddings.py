import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    dot = np.dot(a_np, b_np)
    norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def batch_cosine_similarity(query: list[float], candidates: list[list[float]]) -> list[float]:
    """Compute cosine similarity between a query and multiple candidates."""
    query_np = np.array(query)
    candidates_np = np.array(candidates)
    norms = np.linalg.norm(candidates_np, axis=1)
    query_norm = np.linalg.norm(query_np)
    if query_norm == 0:
        return [0.0] * len(candidates)
    dots = candidates_np @ query_np
    return (dots / (norms * query_norm)).tolist()
