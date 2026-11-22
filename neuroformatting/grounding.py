from typing import Dict, Iterable, List, Optional, Tuple


def build_indexed_sources(source_ids: Iterable[str]) -> Tuple[Dict[int, str], List[int]]:
    """Maps 1..n prompt indices to real source IDs so models choose from an enum index."""
    index_to_id: Dict[int, str] = {}
    for idx, real_id in enumerate(source_ids, start=1):
        index_to_id[idx] = real_id
    return index_to_id, list(index_to_id.keys())


def resolve_source_index(index: int, index_to_id: Dict[int, str]) -> Optional[str]:
    """Resolves a 1..n enum index back to the real source ID in application code."""
    if isinstance(index, bool) or not isinstance(index, int):
        return None
    return index_to_id.get(index)
