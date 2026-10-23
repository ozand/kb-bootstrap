import unittest
from unittest.mock import patch
from kb_bootstrap.local_retrieval import MAX_OUTPUT, json_bytes
from kb_bootstrap.section_projection_reporting import report_section_projection

DIGEST = "a" * 64
def success(status="COMPLETE", **updates):
    value = {"status": status, "path": "guide.md", "observed_sha256": DIGEST, "heading_path": ["Setup"], "occurrence": 1, "start_line": 1, "end_line": 2, "text": "# Setup\nSteps\n", "truncated": status == "TRUNCATED"}
    value.update(updates)
    return value

class SectionProjectionReportingTests(unittest.TestCase):
    def report(self, state="CONFIGURED", required=True, result=None):
        return report_section_projection(selection_state=state, required=required, result=result)

    def test_all_operation_statuses_map_without_collapsing_outcomes(self):
        cases = [({"status":"BLOCKED","reason":"blocked"},"UNKNOWN"), ({"status":"UNSUPPORTED","reason":"unsupported"},"UNKNOWN"), ({"status":"NOT_FOUND","reason":"not_found"},"UNKNOWN"), ({"status":"AMBIGUOUS","reason":"ambiguous"},"UNKNOWN"), ({"status":"REVISION_MISMATCH","observed_sha256":DIGEST},"UNKNOWN"), (success(),"AVAILABLE"), (success("TRUNCATED"),"UNKNOWN")]
        for result, observation in cases:
            with self.subTest(status=result["status"]):
                report=self.report(result=result); self.assertEqual(report["operation_status"],result["status"]); self.assertEqual(report["observation"],observation); self.assertEqual(report["requirement_satisfied"],result["status"]=="COMPLETE")

    def test_not_run_cross_product_and_optional_satisfaction(self):
        keys={"selection_state","required","operation","operation_status","observation","requirement_satisfied"}
        for state in ("NOT_CONFIGURED","DISABLED","CONFIGURED"):
            for required in (False,True):
                r=self.report(state,required); self.assertEqual(set(r),keys); self.assertEqual((r["operation_status"],r["observation"]),("NOT_RUN","NOT_RUN")); self.assertEqual(r["requirement_satisfied"],not required)
        for result in (success(),success("TRUNCATED"),{"status":"NOT_FOUND","reason":"not_found"}): self.assertTrue(self.report(required=False,result=result)["requirement_satisfied"])

    def test_invalid_selection_requirement_and_contradictory_result(self):
        for state in (None,"BROKEN",1):
            with self.assertRaises(ValueError): self.report(state=state)
        for required in (1,0,None):
            with self.assertRaises(ValueError): self.report(required=required)
        for state in ("NOT_CONFIGURED","DISABLED"):
            with self.assertRaises(ValueError): self.report(state=state,result=success())

    def test_result_shapes_statuses_and_bounds(self):
        valid=[{"status":"BLOCKED","reason":"blocked"},{"status":"UNSUPPORTED","reason":"unsupported"},{"status":"NOT_FOUND","reason":"not_found"},{"status":"AMBIGUOUS","reason":"ambiguous"},{"status":"REVISION_MISMATCH","observed_sha256":DIGEST},success(),success("TRUNCATED")]
        for item in valid:
            for bad in (dict(item,extra=True),{k:v for k,v in item.items() if k != next(iter(item))}):
                with self.assertRaises(ValueError): self.report(result=bad)
        bads=[{"status":"BROKEN"},{"status":"NOT_FOUND","reason":"broken"},{"status":"REVISION_MISMATCH","observed_sha256":"A"*64}]
        for changes in ({"occurrence":True},{"start_line":False},{"end_line":0},{"occurrence":0},{"end_line":1,"start_line":2},{"heading_path":("Setup",)},{"heading_path":["x"]*7},{"truncated":True},{"path":""},{"heading_path":[""]},{"observed_sha256":"A"*64}): bads.append(success(**changes))
        for bad in bads:
            with self.assertRaises(ValueError): self.report(result=bad)
        self.assertEqual(self.report(result=success(heading_path=["é"*256]))["operation_status"],"COMPLETE")
        with self.assertRaises(ValueError): self.report(result=success(heading_path=["é"*257]))
        self.assertEqual(self.report(result=success(text="é"*32768))["operation_status"],"COMPLETE")
        with self.assertRaises(ValueError): self.report(result=success(text="é"*32769))
        surrogate=chr(0xd800)
        for changes in ({"text":surrogate},{"path":surrogate},{"heading_path":[surrogate]}):
            with self.assertRaises(ValueError): self.report(result=success(**changes))
        path_bytes = MAX_OUTPUT - len(json_bytes(success(path=""))) - 1
        exact_size = success(path="x" * path_bytes)
        self.assertEqual(len(json_bytes(exact_size)) + 1, MAX_OUTPUT)
        self.assertEqual(self.report(result=exact_size)["operation_status"], "COMPLETE")
        with self.assertRaises(ValueError): self.report(result=dict(exact_size, path=exact_size["path"] + "x"))

    def test_output_privacy_input_immutability_and_no_projection(self):
        value=success(); before=dict(value)
        with patch("kb_bootstrap.section_projection.project_section",side_effect=AssertionError("executed")), patch("builtins.open",side_effect=AssertionError("I/O")), patch("os.open",side_effect=AssertionError("I/O")), patch("subprocess.run",side_effect=AssertionError("process")):
            output=self.report(result=value)
        self.assertEqual(value,before); self.assertNotIn("path",output); self.assertNotIn("text",output); self.assertEqual(len(output),6)

if __name__ == "__main__": unittest.main()
