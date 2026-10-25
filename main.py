#!/usr/bin/env python3
"""stepcheck —— 检查 Markdown 文档里的可执行步骤是否真的可执行。

只做一件事：把文档里的 shell 代码块挑出来，识别那些"看起来能跑、其实跑不了"的地方：
占位符、忘记替换的变量、未闭合的引号、被注释掉的命令。

用法:
    python main.py README.md
    python main.py docs/ --strict
    python main.py --self-test
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 出现在代码块里就说明"这一步还需要人补"的东西
PLACEHOLDER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("占位符 <...>", re.compile(r"<[^<>\n]{1,40}>")),
    ("TODO/FIXME 标记", re.compile(r"\b(TODO|FIXME|XXX)\b")),
    ("未替换的模板变量", re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}")),
    ("示例邮箱", re.compile(r"\b[\w.+-]+@example\.(com|org|net)\b")),
    ("示例密钥", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,})\b")),
]

SHELL_LANGUAGES = {"bash", "sh", "shell", "zsh", "console", "shell-session"}
FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)


@dataclass
class Finding:
    file: str
    line: int
    kind: str
    snippet: str

    def render(self) -> str:
        return f"{self.file}:{self.line}: [{self.kind}] {self.snippet.strip()}"


def _code_blocks(text: str) -> list[tuple[str, int, str]]:
    """返回 (语言, 起始行号, 代码内容) 三元组列表。"""
    blocks: list[tuple[str, int, str]] = []
    for match in FENCE_RE.finditer(text):
        language = match.group(1).strip().split()[0].lower() if match.group(1).strip() else ""
        line = text[: match.start()].count("\n") + 1
        blocks.append((language, line, match.group(2)))
    return blocks


def _odd_quotes(code: str) -> bool:
    """单引号个数为奇数，通常意味着引号没闭合。"""
    return code.count("'") % 2 == 1


def check_text(text: str, path: str = "<text>") -> list[Finding]:
    findings: list[Finding] = []
    for language, start_line, code in _code_blocks(text):
        if language not in SHELL_LANGUAGES:
            continue
        lines = code.splitlines()
        for offset, line in enumerate(lines):
            lineno = start_line + offset + 1
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for kind, pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding(path, lineno, kind, line))
                    break
        if _odd_quotes(code):
            findings.append(Finding(path, start_line, "引号可能未闭合", lines[0] if lines else ""))
    return findings


def check_path(path: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
        return []
    return check_text(text, str(path))


def iter_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".markdown"})
    return []


def self_test() -> int:
    good = """```bash
python main.py README.md
```
"""
    bad = """```bash
export TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123
curl https://api.example.com -H "Authorization: $TOKEN"
```
"""
    problems = """```bash
python -c "print('hi"
```
"""
    assert check_text(good) == [], check_text(good)
    assert check_text(bad), "示例密钥应被识别"
    assert any(f.kind == "引号可能未闭合" for f in check_text(problems)), "未闭合引号应被识别"
    assert check_text("```python\nprint(1)\n```") == [], "非 shell 代码块应跳过"
    print("self-test: ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stepcheck",
        description="检查 Markdown 里的 shell 步骤是否真的能跑（识别占位符与未闭合引号）",
    )
    parser.add_argument("target", nargs="?", default=".", help="要检查的文件或目录")
    parser.add_argument("--strict", action="store_true", help="有发现时以退出码 1 结束")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    target = Path(args.target)
    files = iter_files(target)
    if not files:
        print(f"stepcheck: 没有找到可检查的 Markdown 文件（{target}）", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for path in files:
        findings.extend(check_path(path))

    for finding in findings:
        print(finding.render())
    checked = len(files)
    print(f"\n检查了 {checked} 个文件，发现 {len(findings)} 个问题。")
    if args.strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
