"""stepcheck 的单元测试。零依赖，直接 python test_stepcheck.py 运行。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import check_text, iter_files  # noqa: E402


DOC_OK = """# 标题

```bash
python main.py README.md
```
"""

DOC_PLACEHOLDER = """# 标题

```bash
curl <your-endpoint>
```
"""

DOC_TOKEN = """```bash
export TOKEN=${GITHUB_TOKEN}
```
"""

DOC_TODO = """```bash
export KEY=XXX
```
"""

DOC_EMAIL = """```bash
git config user.email you@example.com
```
"""

DOC_SECRET = """```bash
export TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123
```
"""

DOC_UNCLOSED = """```bash
echo "abc
```
"""

DOC_PY = """```python
print("<not-a-placeholder>")
```
"""

DOC_COMMENT = """```bash
# TODO: 这里还没写完
```
"""


class TestCheckText(unittest.TestCase):
    def test_clean_doc_has_no_findings(self):
        self.assertEqual(check_text(DOC_OK), [])

    def test_placeholder_detected(self):
        found = check_text(DOC_PLACEHOLDER)
        self.assertTrue(found)
        self.assertEqual(found[0].kind, "占位符 <...>")

    def test_template_variable_detected(self):
        found = check_text(DOC_TOKEN)
        self.assertTrue(found)
        self.assertEqual(found[0].kind, "未替换的模板变量")

    def test_todo_marker_detected(self):
        found = check_text(DOC_TODO)
        self.assertTrue(found)
        self.assertEqual(found[0].kind, "TODO/FIXME 标记")

    def test_example_email_detected(self):
        found = check_text(DOC_EMAIL)
        self.assertTrue(found)
        self.assertEqual(found[0].kind, "示例邮箱")

    def test_secret_detected(self):
        found = check_text(DOC_SECRET)
        self.assertTrue(found)
        self.assertEqual(found[0].kind, "示例密钥")

    def test_unclosed_quote_detected(self):
        found = check_text(DOC_UNCLOSED)
        self.assertTrue(found)
        self.assertTrue(any("引号可能未闭合" in f.kind for f in found))

    def test_quote_inside_other_quote_type_not_flagged(self):
        doc = """```bash
awk '{print \"x\"}' file
```
"""
        self.assertEqual(check_text(doc), [])

    def test_escaped_quote_not_flagged(self):
        doc = """```bash
echo \\"quoted\\"
```
"""
        self.assertEqual(check_text(doc), [])

    def test_non_shell_block_ignored(self):
        self.assertEqual(check_text(DOC_PY), [])

    def test_commented_line_ignored(self):
        self.assertEqual(check_text(DOC_COMMENT), [])

    def test_line_number_points_at_placeholder(self):
        found = check_text(DOC_PLACEHOLDER)
        self.assertEqual(found[0].line, 4)

    def test_finding_renders_file_line_and_kind(self):
        found = check_text(DOC_PLACEHOLDER, "docs/x.md")
        self.assertIn("docs/x.md:4:", found[0].render())
        self.assertIn("占位符", found[0].render())


class TestIterFiles(unittest.TestCase):
    def test_iter_files_accepts_file(self):
        p = Path(__file__).resolve().parent / "README.md"
        self.assertEqual(iter_files(p), [p])

    def test_iter_files_empty_for_missing_target(self):
        self.assertEqual(iter_files(Path("definitely-not-here-xyz")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
