import unittest

from neuroformatting import build_indexed_sources, resolve_source_index


class TestGroundingHelpers(unittest.TestCase):
    def test_index_mapping_and_resolution(self) -> None:
        mapping, allowed_indices = build_indexed_sources(["doc-101", "doc-202"])
        self.assertEqual(allowed_indices, [1, 2])
        self.assertEqual(resolve_source_index(1, mapping), "doc-101")
        self.assertIsNone(resolve_source_index(99, mapping))
        self.assertIsNone(resolve_source_index(True, mapping))


if __name__ == "__main__":
    unittest.main()
