# Git 学习笔记

- `git status` 用于查看当前工作区和暂存区状态，判断文件是否修改、删除或新增。
- `git branch` 显示本地分支列表，`git branch -r` 显示远端分支。
- `git checkout <branch>` 切换分支，`git switch <branch>` 是更现代的命令。
- `git checkout -b <new-branch>` 或 `git switch -c <new-branch>` 创建并切换到新分支。
- `git add <file>` 将变更放入暂存区，`git reset <file>` 撤销暂存区中的文件。
- 合并冲突时，编辑冲突文件，保留正确内容后使用 `git add <file>` 标记为已解决。
- 解决完成后，执行 `git commit` 完成合并提交。
- `git log --oneline --graph --decorate` 可以可视化分支和提交历史，帮助定位冲突来源。
- 养成经常提交小步改动、写清晰提交信息的习惯，有助于后续回滚和冲突处理。
