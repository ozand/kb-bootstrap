import copy
import unittest
from kb_bootstrap.evidence_review import compose_evidence_review_worklist
D1, D2 = "1" * 64, "2" * 64

def ref(source, state, digest=D1, binding="b1"):
    reason = {"unchanged":"byte_revision_matches", "changed":"byte_revision_differs", "missing":"current_mapping_absent"}[state]
    row = {"binding_id":binding,"source_id":source,"representation_id":"r1","observed_sha256":digest,"raw_path":"raw/e.md","state":state,"reason":reason}
    row["current"] = {"source_id":"cur","representation_id":"r2"} if state == "missing" else {"source_id":"cur","representation_id":"r2","observed_sha256":D2 if state == "changed" else digest,"raw_path":"current/e.md"}
    return row

def report(rows, summary=None):
    rows = sorted(rows,key=lambda x:(x["source_id"],x["representation_id"],x["observed_sha256"],x["binding_id"]))
    summary = summary or ("changed" if any(x["state"]=="changed" for x in rows) else "missing" if any(x["state"]=="missing" for x in rows) else "unchanged")
    knowledge = {"path":"kb/note.md","summary":summary}
    if summary == "changed" and not any(x["state"]=="changed" for x in rows): knowledge["observed_sha256"] = D2
    return {"status":"COMPLETE","knowledge":knowledge,"references":rows}

class EvidenceReviewTests(unittest.TestCase):
    graph = [{"id":"root","kind":"independent","upstream_ids":[]},{"id":"copy","kind":"reprint","upstream_ids":["root"]}]
    def compose(self, rep, graph=None, complete=True, mapping=None):
        return compose_evidence_review_worklist(rep,self.graph if graph is None else graph,complete,{} if mapping is None else mapping)
    def test_worklist_preserves_rows_and_marks_review(self):
        original=report([ref("a","changed"),ref("b","unchanged")]); before=copy.deepcopy(original)
        out=self.compose(original,mapping={("a","r1"):"copy"})
        self.assertEqual(out["resolver_report"],before); self.assertTrue(out["worklist"][0]["review_required"])
        self.assertFalse(out["worklist"][1]["review_required"]); self.assertEqual(out["worklist"][0]["lineage"]["root_ids"],["root"])
        out["worklist"][0]["reference"]["current"]["raw_path"]="mutated"; self.assertEqual(original,before)

    def test_unmapped_and_incomplete_are_unknown(self):
        rep=report([ref("a","unchanged")])
        self.assertEqual(self.compose(rep)["worklist"][0]["lineage"],{"state":"unknown"})
        out=self.compose(rep,complete=False,mapping={("a","r1"):"copy"})
        self.assertEqual(out["worklist"][0]["lineage"],{"id":"copy","state":"unknown"})

    def test_changed_document_requires_separate_review(self):
        out=self.compose(report([ref("a","unchanged")],"changed"))
        self.assertTrue(out["knowledge_review_required"]); self.assertFalse(out["worklist"][0]["review_required"])

    def test_missing_review_and_blocked_validation_order(self):
        self.assertTrue(self.compose(report([ref("a","missing")]))["worklist"][0]["review_required"])
        blocked={"status":"BLOCKED","reason":"invalid_binding"}
        self.assertEqual(self.compose(blocked)["worklist"],[])
        with self.assertRaises(ValueError): self.compose(blocked,graph=[{"id":"x","kind":"reprint","upstream_ids":["absent"]}])
        with self.assertRaises(ValueError): self.compose(blocked,mapping={("x","y"):"root"})
    def test_strict_report_shape_states_and_summary(self):
        good=report([ref("a","unchanged")]); self.assertEqual(self.compose(good)["resolver_report"],good)
        bad=[]
        item=copy.deepcopy(good); item["extra"]=1; bad.append(item)
        item=copy.deepcopy(good); item["references"][0]["reason"]="unknown"; bad.append(item)
        item=copy.deepcopy(good); item["references"][0]["current"]["observed_sha256"]=D2; bad.append(item)
        item=copy.deepcopy(good); item["references"][0]["current"]["observed_sha256"]=D1; item["references"][0]["state"]="changed"; item["references"][0]["reason"]="byte_revision_differs"; item["knowledge"]["summary"]="changed"; item["knowledge"]["observed_sha256"]=D2; bad.append(item)
        item=report([ref("a","missing")]); item["knowledge"]["summary"]="unchanged"; bad.append(item)
        bad.append({"status":"BLOCKED","reason":"unknown"})
        for index, value in enumerate(bad):
            with self.subTest(value=value), self.assertRaises(ValueError, msg=str(index)): self.compose(value)

    def test_mapping_validation_copy_and_caps(self):
        rep=report([ref("a","unchanged")])
        for mapping in ({("extra","r1"):"root"},{("a","r1"):"absent"},{("a","r1"):True},{("a",):"root"},{"a":"root"}):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError): self.compose(rep,mapping=mapping)
        graph=copy.deepcopy(self.graph); mapping={("a","r1"):"copy"}; before=copy.deepcopy((rep,graph,mapping))
        out=self.compose(rep,graph=graph,mapping=mapping); out["resolver_report"]["references"][0]["current"]["raw_path"]="changed"
        out["worklist"][0]["lineage"]["root_ids"].append("bad"); self.assertEqual((rep,graph,mapping),before)
        self.assertEqual(len(self.compose(report([ref(f"s{i:04}","unchanged") for i in range(999)]))["worklist"]),999)
        with self.assertRaises(ValueError): self.compose(report([ref(f"s{i:04}","unchanged") for i in range(1000)]))

    def test_reference_order_is_validated(self):
        value={"status":"COMPLETE","knowledge":{"path":"kb/note.md","summary":"unchanged"},"references":[ref("z","unchanged"),ref("a","unchanged")]}
        with self.assertRaises(ValueError): self.compose(value)

    def test_graph_validated_with_complete_report(self):
        with self.assertRaises(ValueError): self.compose(report([ref("a","unchanged")]),graph=[{"id":"bad","kind":"reprint","upstream_ids":["absent"]}])

    def test_real_resolver_composition_with_duplicate_binding(self):
        from test_evidence_binding import EvidenceBindingTests
        fixture=EvidenceBindingTests(); fixture.setUp()
        try:
            second=dict(fixture.binding["bindings"][0]["evidence"][0])
            second.update(source_id="source-steady",representation_id="rep-steady",current={"source_id":"source-steady-current","representation_id":"rep-steady-current"})
            fixture.binding["bindings"].append({"binding_id":"binding-2","evidence":[second]})
            fixture._write_binding(); changed=b"Evidence changed.\n"
            (fixture.base_project/"corpus/steady.md").write_bytes(fixture.base_bytes)
            (fixture.current_project/"corpus/evidence.md").write_bytes(changed)
            (fixture.current_project/"corpus/steady.md").write_bytes(fixture.base_bytes)
            fixture._write_envelope(fixture.base_meta,"source-base","rep-base",fixture.base_bytes)
            base_text=fixture.base_meta.read_text(encoding="utf-8")
            base_source=base_text[base_text.index("- source_id:"):].replace("source-base","source-steady").replace("rep-base","rep-steady").replace("raw_path: evidence.md","raw_path: steady.md")
            fixture.base_meta.write_text(base_text+base_source,encoding="utf-8")
            fixture._write_envelope(fixture.current_meta,"source-current","rep-current",changed)
            current_text=fixture.current_meta.read_text(encoding="utf-8")
            current_source=current_text[current_text.index("- source_id:"):].replace("source-current","source-steady-current").replace("rep-current","rep-steady-current").replace("raw_path: evidence.md","raw_path: steady.md").replace(__import__("hashlib").sha256(changed).hexdigest(),__import__("hashlib").sha256(fixture.base_bytes).hexdigest())
            fixture.current_meta.write_text(current_text+current_source,encoding="utf-8")
            resolver_report=fixture.resolve(baseline_selected_paths=["evidence.md","steady.md"],current_selected_paths=["evidence.md","steady.md"])
            self.assertEqual([x["state"] for x in resolver_report["references"]],["changed","unchanged"])
            graph=[{"id":"root","kind":"independent","upstream_ids":[]},{"id":"copy","kind":"reprint","upstream_ids":["root"]}]
            out=self.compose(resolver_report,graph=graph,mapping={("source-base","rep-base"):"copy"})
            self.assertEqual([row["review_required"] for row in out["worklist"]],[True,False])
            self.assertEqual(out["worklist"][0]["lineage"]["root_ids"],["root"])
            self.assertEqual(out["worklist"][1]["lineage"],{"state":"unknown"})
        finally: fixture.doCleanups()
