# stepcheck

一个只做一件事的小工具：**检查 Markdown 文档里的 shell 步骤是不是真的能跑。**

写教程的人都有过这种时刻——文档看起来很完整，读者复制命令过去，第一行就报 `command not found`。
多数时候不是环境问题，而是文档本身还留着没替换的占位符、少一个引号、或者命令被注释掉了。

`stepcheck` 把这类"纸面上能跑、实际上跑不了"的地方挑出来。

- 零依赖，只用 Python 标准库
- 单文件，约 200 行，可以直接内嵌进你自己的 CI
- 不联网，不上传任何内容，只读本地文件

## 为什么还要做这个

现成的 Markdown lint 工具（`markdownlint`、`remark`）主要管**格式**：标题层级、列表缩进、空行。
它们不检查代码块的**语义**——`curl -H "Authorization: $TOKEN"` 里的 `$TOKEN` 有没有赋值、
引号有没有闭合、`ghp_xxx` 这种示例密钥是不是忘了打码。

`stepcheck` 补的是这一段：从"这是合法的 Markdown"到"这条命令能跑"之间的那一步。

它刻意不做什么：不做 shell 语法解析（那是 `shellcheck` 的活，而且需要真的装 shell），
不联网执行命令（那会产生副作用），不判断你的业务逻辑对不对。

## 用法

```bash
# 检查单个文件
python main.py README.md

# 检查整个目录下的所有 Markdown
python main.py docs/

# 发现问题时用非零退出码，可以直接接进 CI
python main.py docs/ --strict

# 跑内置自检，确认这份代码本身还活着
python main.py --self-test
```

输出长这样：

```
docs/deploy.md:42: [未替换的模板变量] export TOKEN=${GITHUB_TOKEN}
docs/deploy.md:51: [引号可能未闭合（双引号）] curl -H "Authorization: $TOKEN
检查了 12 个文件，发现 2 个问题。
```

## 检查项

| 类型 | 例子 | 为什么要在意 |
|---|---|---|
| 占位符 `<...>` | `curl <your-endpoint>` | 读者复制过去必然失败 |
| `TODO` / `FIXME` / `XXX` | `export KEY=XXX` | 明确标记了"还没写完" |
| 未替换的模板变量 | `${GITHUB_TOKEN}` | 通常意味着漏了赋值步骤 |
| 示例邮箱 | `you@example.com` | 容易残留到真实文档 |
| 疑似真实密钥 | `ghp_...` / `gho_...` | 泄密的最后一道拦板 |
| 引号未闭合 | `echo "abc` | shell 里会静默吞掉后面的内容 |

只检查 ```` ```bash ```` / ```` ```sh ```` / ```` ```shell ```` / ```` ```console ```` 这几类代码块，
Python、JSON 等其他语言块一律跳过——`${...}` 在很多语言里是合法语法。

## 局限（请务必看一眼）

- **不执行命令**。所以它能发现"占位符没填"，发现不了"命令本身写错了"。
- **不解析 shell**。`if` / `for` / 函数体内的引号可能误报。
- **误报存在**。引号检测用的是状态机：`awk '{print "x"}'` 里双引号在单引号内部，不算未闭合；
  但跨行的字符串拼接、heredoc 里的引号仍可能被误判。
- 密钥检测靠的是前缀模式，只覆盖 GitHub token 的常见格式。

有误报就当噪音处理，先看它报的**行号**——那一行确实值得人看一眼。

## 跑测试

```bash
python test_stepcheck.py
```

15 个用例，覆盖占位符、模板变量、TODO 标记、示例邮箱、示例密钥、未闭合引号、
非 shell 代码块跳过、注释行跳过、行号定位等行为。

## 作为库使用

```python
from main import check_text, check_path

findings = check_text(open("README.md", encoding="utf-8").read(), "README.md")
for f in findings:
    print(f.file, f.line, f.kind)
```

`check_text` 是纯函数，不碰文件系统，方便你塞进自己的检查流水线。

---

## 关于作者

janvangen 写可复现的技术实践，做能直接用的开源小工具。这个工具只做一件事：把文档里跑不通的 shell 步骤挑出来。

- 个人主页：<https://janvangen.github.io>
- 仓库：<https://github.com/janvangen/stepcheck>

## 许可

MIT，见 [LICENSE](LICENSE)。
