"""Compare work-start hashes and original interactive widget contracts."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/visual_reskin"
WIDGETS = {
    "radio",
    "button",
    "file_uploader",
    "text_area",
    "selectbox",
    "checkbox",
    "download_button",
}


def widget_contracts(source):
    calls = [
        n
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in WIDGETS
    ]
    return sorted(
        (
            n.func.attr,
            ast.dump(ast.Tuple(elts=n.args)),
            tuple((k.arg, ast.dump(k.value)) for k in n.keywords),
        )
        for n in calls
    )


def main():
    baseline = json.loads((OUT / "before_hashes.json").read_text(encoding="utf8"))
    changed = [
        p
        for p, digest in baseline.items()
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest
    ]
    protected = [p for p in baseline if not p.startswith("frontend/") or p.endswith(".js")]
    assert not (set(protected) & set(changed)), changed
    assert set(changed) <= {"frontend/app.py", "frontend/readable_text.py"}, changed
    before = (OUT / "before/frontend/app.py").read_text(encoding="utf8")
    after = (ROOT / "frontend/app.py").read_text(encoding="utf8")
    assert widget_contracts(before) == widget_contracts(after), (
        "Widget arguments/keys/callbacks changed"
    )
    # Existing logic functions must retain their entire AST. Only the upload
    # function has presentation wrappers, validated by widget contracts + smoke.
    old = {n.name: n for n in ast.parse(before).body if isinstance(n, ast.FunctionDef)}
    new = {n.name: n for n in ast.parse(after).body if isinstance(n, ast.FunctionDef)}
    for name in old.keys() - {"upload_documents"}:
        assert ast.dump(old[name]) == ast.dump(new[name]), name
    report = {
        "result": "PASS",
        "protected_files": len(protected),
        "changed_existing_files": changed,
        "interactive_widget_calls": len(widget_contracts(before)),
        "keys_callbacks_arguments_identical": True,
        "js_event_handlers_unchanged": True,
        "backend_and_expected_unchanged": True,
    }
    (OUT / "functional_diff.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
