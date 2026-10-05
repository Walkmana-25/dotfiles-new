---
description: Stage all changes and create a commit. The orchestrator reviews the diff, generates the message, and runs every git operation itself (no delegation of git commands).
---

You are the orchestrator agent performing an automated commit workflow. Follow these steps exactly in order:

1. Review all current changes YOURSELF by running: git status, git diff, and (if something is staged) git diff --cached. This covers staged changes, unstaged changes, and untracked files. Do NOT delegate git commands to subagents.

2. Write a concise, conventional-commit-style commit message from the diff YOURSELF. Only if the diff is very large, you MAY use the commit-diff-reader subagent to summarize the diff and the commit-message-generator subagent to draft the message — these subagents are strictly READ-ONLY and must never run git write commands.

3. Stage all changes YOURSELF by running: git add -A

4. Commit YOURSELF using a heredoc to pass the message directly without creating any temporary file. Run the following bash command (replace <message> with the actual commit message):
git commit -F - << 'COMMIT_MSG_EOF'
<message>
COMMIT_MSG_EOF
The heredoc delimiter COMMIT_MSG_EOF must be on its own line with no leading/trailing whitespace. Do NOT create any temporary files. Do NOT delegate this to any subagent.

5. Display the result by running: git log -1 --stat

Report the final commit that was made.
