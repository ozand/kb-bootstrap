"""Contract tests for the pure ADR-040 caller-declared lineage helper."""

import copy
import unittest

from kb_bootstrap.evidence_lineage import classify_evidence_lineage


class EvidenceLineageTests(unittest.TestCase):
    def test_generated_and_reprint_inherit_declared_roots(self):
        records = [
            {"id": "r", "kind": "reprint", "upstream_ids": ["g"]},
            {"id": "g", "kind": "generated", "upstream_ids": ["a"]},
            {"id": "a", "kind": "independent", "upstream_ids": []},
            {"id": "b", "kind": "independent", "upstream_ids": []},
            {"id": "m", "kind": "generated", "upstream_ids": ["a", "b"]},
        ]
        before = copy.deepcopy(records)
        result = classify_evidence_lineage(records, True)
        self.assertEqual(records, before)
        self.assertEqual([row["id"] for row in result], ["a", "b", "g", "m", "r"])
        self.assertEqual(result[0], {"id": "a", "state": "classified", "root_ids": ["a"], "root_count": 1})
        self.assertEqual(result[2]["root_ids"], ["a"])
        self.assertEqual(result[3]["root_ids"], ["a", "b"])
        self.assertEqual(result[4]["root_ids"], ["a"])

    def test_invalid_or_cyclic_graph_is_rejected(self):
        invalid = [
            None,
            {"id": "a", "kind": "independent", "upstream_ids": []},
            [{"id": "a", "kind": "independent", "upstream_ids": [], "extra": 1}],
            [{"id": "a", "kind": "independent", "upstream_ids": ["a"]}],
            [{"id": "a", "kind": "generated", "upstream_ids": []}],
            [{"id": "a", "kind": "independent", "upstream_ids": ["b"]}],
            [{"id": "a", "kind": "independent", "upstream_ids": []}] * 2,
            [
                {"id": "a", "kind": "independent", "upstream_ids": []},
                {"id": "g", "kind": "generated", "upstream_ids": []},
            ],
            [
                {"id": "a", "kind": "independent", "upstream_ids": []},
                {"id": "r", "kind": "reprint", "upstream_ids": ["a"]},
                {"id": "g", "kind": "generated", "upstream_ids": ["r", "r"]},
            ],
            [{"id": "a" * 257, "kind": "independent", "upstream_ids": []}],
            [
                {"id": "a", "kind": "generated", "upstream_ids": ["b"]},
                {"id": "b", "kind": "reprint", "upstream_ids": ["a"]},
            ],
            [{"id": "bad\n", "kind": "independent", "upstream_ids": []}],
            [{"id": True, "kind": "independent", "upstream_ids": []}],
            [{"id": "a", "kind": "independent", "upstream_ids": ["b", "b"]}],
        ]
        for records in invalid:
            with self.subTest(records=records):
                with self.assertRaises(ValueError):
                    classify_evidence_lineage(records, True)
        with self.assertRaises(ValueError):
            classify_evidence_lineage([], 1)

    def test_incomplete_coverage_never_classifies_independence(self):
        result = classify_evidence_lineage(
            [{"id": "a", "kind": "independent", "upstream_ids": []}], False
        )
        self.assertEqual(result, [{"id": "a", "state": "unknown"}])
        self.assertEqual(classify_evidence_lineage([], True), [])

    def test_graph_limits_and_maximum_chain(self):
        chain = [{"id": "n0000", "kind": "independent", "upstream_ids": []}]
        for index in range(1, 1000):
            chain.append({
                "id": f"n{index:04}",
                "kind": "generated" if index % 2 else "reprint",
                "upstream_ids": [f"n{index - 1:04}"],
            })
        result = classify_evidence_lineage(chain, True)
        self.assertEqual(len(result), 1000)
        self.assertEqual(result[-1]["root_ids"], ["n0000"])
        with self.assertRaises(ValueError):
            classify_evidence_lineage(chain + [{"id": "extra", "kind": "independent", "upstream_ids": []}], True)
        fanin = [{"id": f"r{i}", "kind": "independent", "upstream_ids": []} for i in range(101)]
        fanin.append({"id": "g", "kind": "generated", "upstream_ids": [f"r{i}" for i in range(100)]})
        result = classify_evidence_lineage(fanin, True)
        self.assertEqual(next(row for row in result if row["id"] == "g")["root_count"], 100)
        fanin[-1]["upstream_ids"].append("r100")
        with self.assertRaises(ValueError):
            classify_evidence_lineage(fanin, True)

    def test_lineage_classification_is_order_independent(self):
        records = [
            {"id": "a", "kind": "independent", "upstream_ids": []},
            {"id": "b", "kind": "independent", "upstream_ids": []},
            {"id": "g", "kind": "generated", "upstream_ids": ["b", "a"]},
            {"id": "r", "kind": "reprint", "upstream_ids": ["g"]},
        ]
        reordered = [dict(row, upstream_ids=list(reversed(row["upstream_ids"]))) for row in reversed(records)]
        self.assertEqual(classify_evidence_lineage(records, True), classify_evidence_lineage(reordered, True))


if __name__ == "__main__":
    unittest.main()
