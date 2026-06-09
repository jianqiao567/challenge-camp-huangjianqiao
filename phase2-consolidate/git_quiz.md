# Git 笔试答案

1. 如何查看当前分支？

- 使用 `git branch`，当前分支前面会有 `*` 标记。
- 也可以使用 `git status`，输出中会显示当前所在分支名称。

2. 如何创建并切换到新分支？

- 使用 `git checkout -b <branch-name>`。
- 或使用更现代的命令：`git switch -c <branch-name>`。

3. 合并时出现冲突怎么办？（写出详细步骤）

- 运行 `git merge <branch-name>`。
- 如果出现冲突，`git status` 会列出冲突文件。
- 打开冲突文件，找到冲突标记 `<<<<<<<`, `=======`, `>>>>>>>`。
- 手工选择保留的代码，删除冲突标记，并整理成正确版本。
- 保存文件后，执行 `git add <file>` 标记冲突已解决。
- 对所有冲突文件都执行 `git add`。
- 然后运行 `git commit` 完成合并提交；如果是合并请求，可能只需 `git commit` 或 `git merge --continue`。
- 如果合并方向错误或无法解决，可使用 `git merge --abort` 撤销合并操作，回到合并前状态。

4. 如何撤销暂存区的文件？

- 使用 `git reset <file>` 将文件从暂存区撤回到工作区。
- 如果要撤销所有暂存内容，使用 `git reset`。

5. .gitignore 的作用是什么？

- `.gitignore` 用于告诉 Git 忽略指定的文件或目录，不将它们添加到版本控制。
- 常用来排除生成文件、临时文件、个人配置和敏感信息，例如 `__pycache__/`, `*.pyc`, `.vscode/`, `.env` 等。
