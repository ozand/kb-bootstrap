"""W11 characterization, not permission to harmonize public contracts."""
import io
import json
import tempfile
import unittest
import subprocess
import sys
import zipfile
import shutil
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

    def validate_canonical_profile_with_old_brief(self, root, brief):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'kb'
            shutil.copytree(root, copy)
            old_brief = copy / brief.relative_to(root)
            text = old_brief.read_text(encoding='utf-8')
            text = text.replace('status: draft\nworkflow_status: in-progress\n', 'status: in-progress\n')
            old_brief.write_text(text, encoding='utf-8')
            return validate_canonical_profile(copy)

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

    def test_generated_research_workflow_role_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            root = workspace / 'kb'
            (root / 'wiki').mkdir(parents=True)
            creator = (Path(__file__).parents[1] / 'kb_bootstrap' / 'templates' / 'skills'
                       / 'market-research' / 'scripts' / 'new_research.py')
            completed = subprocess.run(
                [sys.executable, str(creator), 'workflow-study', '--title', 'Workflow study',
                 '--kb', str(root)], cwd=workspace, capture_output=True, text=True, check=True,
            )
            brief = Path(completed.stdout.strip()) / 'brief.md'
            self.assertTrue(brief.is_file())
            self.assertTrue((brief.parent / 'raw' / 'img').is_dir())
            generated_text = brief.read_text(encoding='utf-8')
            self.assertIn('status: draft', generated_text)
            self.assertIn('workflow_status: in-progress', generated_text)

            # Retrieval deliberately excludes research, regardless of document role.
            self.write(root, 'research/study.md', CONCEPT)
            generated_path = brief.relative_to(root).as_posix()
            report = root / 'wiki' / 'reports' / f'{brief.parent.name}.md'
            self.write(
                root, report.relative_to(root).as_posix(),
                CONCEPT + f'[{brief.name}](../../{generated_path})\n',
            )
            self.write(root, 'research/study.md', CONCEPT + 'workflow study canonical counterexample\n')
            self.write(root, 'outside.md', CONCEPT + 'workflow study safe canonical counterexample\n')
            before = {p.relative_to(root).as_posix(): p.read_bytes()
                      for p in root.rglob('*') if p.is_file()}
            profile, profile_ok = validate_canonical_profile(root)
            _, legacy_profile_ok = self.validate_canonical_profile_with_old_brief(root, brief)
            _, lint_validation_ok = validate(root)
            graph = analyze_graph(root)[0]
            lint_ok = lint_validation_ok
            exported, export_report, export_ok = build_canonical_graph(root)
            bundle, bundle_report, bundle_ok = build_published_bundle(root)
            results, search_code = search_local('workflow study', root)
            concept_results, concept_search_code = search_local('canonical counterexample', root)
            after = {p.relative_to(root).as_posix(): p.read_bytes()
                     for p in root.rglob('*') if p.is_file()}

            self.assertTrue(profile_ok, profile)
            self.assertFalse(legacy_profile_ok)
            self.assertTrue(lint_ok)
            self.assertIn(generated_path, graph.nodes)
            self.assertIn(report.relative_to(root).as_posix(), graph.nodes)
            self.assertTrue(export_ok, export_report)
            exported_nodes = {node['path'] for node in json.loads(exported)['nodes']}
            self.assertIn(generated_path, exported_nodes)
            self.assertTrue(bundle_ok, bundle_report)
            with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
                self.assertIn(generated_path, archive.namelist())
            self.assertEqual(search_code, 0)
            result_paths = {row['path'] for row in results['results']}
            self.assertNotIn(generated_path, result_paths)
            self.assertIn('outside.md', result_paths)
            self.assertEqual(concept_search_code, 0)
            self.assertNotIn('research/study.md', {row['path'] for row in concept_results['results']})
            self.assertEqual(before, after)

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

