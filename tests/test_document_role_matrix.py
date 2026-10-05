"""W11 characterization, not permission to harmonize public contracts."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from kb_bootstrap.canonical_profile import validate_canonical_profile
from kb_bootstrap.graph_linter import analyze_graph, validate
from kb_bootstrap.canonical_graph_export import build_canonical_graph
from kb_bootstrap.published_bundle_export import build_published_bundle
from kb_bootstrap.local_retrieval import search_local

CONCEPT = '---\ntype: Concept\n---\nquartzmarker\n'

class DocumentRoleMatrixTests(unittest.TestCase):
    def observe(self, root):
        before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        profile, profile_ok = validate_canonical_profile(root)
        graph, _ = analyze_graph(root)
        _, lint_ok = validate(root)
        exported, export_report, export_ok = build_canonical_graph(root)
        bundle, bundle_report, bundle_ok = build_published_bundle(root)
        results, code = search_local('quartzmarker', root)
        self.assertEqual(code, 0)
        self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()})
        return profile_ok, graph, lint_ok, exported, export_ok, bundle, bundle_ok, results, profile + export_report + bundle_report

    def write(self, root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def test_role_membership_and_workflow_state(self):
        cases = (
            ('research/study.md', CONCEPT, True, True, True, False),
            ('research/brief.md', '---\ntype: Research\nstatus: in-progress\n---\nquartzmarker\n', False, True, False, False),
            ('raw/capture.md', 'quartzmarker', True, False, False, False),
            ('lessons/lesson.md', 'quartzmarker', True, False, False, False),
            ('index.md', '# quartzmarker\n', True, True, True, False),
            ('log.md', '## 2026-09-21\nquartzmarker', True, True, True, False),
            ('ordinary.MD', CONCEPT, True, True, True, True),
        )
        for name, content, valid, lint_node, bundle_member, hit in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.write(root, 'source.md', CONCEPT)
                self.write(root, name, content)
                p, graph, lint, data, exported, bundle, published, result, reports = self.observe(root)
                self.assertEqual((p, lint, exported, published), (valid, True, valid, valid))
                self.assertEqual(name in graph.nodes, lint_node)
                self.assertEqual(name in {r['path'] for r in result['results']}, hit)
                if valid:
                    nodes = {n['path'] for n in json.loads(data)['nodes']}
                    self.assertEqual(name in nodes, lint_node and name not in ('index.md', 'log.md'))
                    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
                        self.assertEqual(name in archive.namelist(), bundle_member)
                else:
                    self.assertEqual((data, bundle), (b'', b''))
                    self.assertIn('status must be draft, stable, or deprecated', reports)

    def test_link_grammar_and_output_boundaries(self):
        cases = (
            ('[x](target.md)', True, True, True, True),
            ('[x](target.md#section)', True, True, True, True),
            ('[x](missing.md)', False, False, False, False),
            ('`[x](missing.md)`', False, True, False, False),
            ('```\n[x](missing.md)\n```', True, True, False, False),
            ('[x](https://example.invalid/missing.md)', True, True, False, False),
            ('[x](target.md "title")', True, True, False, True),
            ('[x](target.MD)', True, True, False, True),
            ('[x](#missing-anchor)', True, True, False, False),
            ('[x](raw/capture.md)', True, False, False, False),
            ('[x](lessons/lesson.md)', False, False, False, False),
        )
        for body, lint_ok, export_ok, lint_edge, export_edge in cases:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.write(root, 'source.md', CONCEPT + body)
                for name in ('target.md', 'target.MD', 'raw/capture.md', 'lessons/lesson.md'):
                    # Use only one spelling per fixture (Windows case-insensitive FS).
                    if name == 'target.md' and 'target.MD' in body:
                        continue
                    if name == 'target.MD' and 'target.MD' not in body:
                        continue
                    self.write(root, name, CONCEPT)
                p, graph, lint, data, exported, bundle, published, result, reports = self.observe(root)
                self.assertTrue(p)
                self.assertEqual((lint, exported, published), (lint_ok, export_ok, True))
                self.assertEqual(bool(graph.edges()), lint_edge)
                if exported:
                    edges = json.loads(data)['edges']
                    self.assertEqual(bool(edges), export_edge)
                    if '#section' in body:
                        self.assertEqual(edges[0]['fragment'], 'section')
                else:
                    self.assertEqual(data, b'')
                with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
                    self.assertNotIn('raw/capture.md', archive.namelist())
                    self.assertNotIn('lessons/lesson.md', archive.namelist())
                if 'raw/capture' in body:
                    self.assertEqual(graph.graph['evidence_links'], {('source.md', 'raw/capture.md')})

