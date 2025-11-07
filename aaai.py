#!/usr/bin/env python3

import subprocess
import sys
import os
from time import sleep

def get_shell():
    """
    检测当前操作系统和shell类型
    Returns: 包含shell可执行文件路径的列表，可直接用于subprocess
    """
    if sys.platform == "win32":
        # Windows系统，使用cmd.exe
        return []
    else:
        # Linux/Mac系统，检测用户的shell
        shell = os.environ.get("SHELL", "").lower()
        if "zsh" in shell:
            return ["zsh", "-c"]
        else:
            # 默认使用bash
            return ["bash", "-c"]

branch = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, capture_output=True
).stdout.strip()

target = "refactor-nightly"
commands = [
    fr'''cat .claude/ar3.md | gemini -m gemini-2.5-flash --approval-mode=yolo''',
    fr'''cat .claude/ar3.md | qwen -m="Qwen/Qwen3-Coder-480B-A35B-Instruct" --approval-mode=yolo -p''',
    fr'''cat .claude/ar3.md | codex exec -m="gpt-5-codex" --dangerously-bypass-approvals-and-sandbox''',
    fr'''cat .claude/ar3.md | claude --permission-mode bypassPermissions -p'''
]

if branch == target:
    print(f"already on {target}")
else:
    exists = subprocess.run(["git", "branch", "--list", target], text=True, capture_output=True ).stdout.strip()
    if exists:
        subprocess.run(["git", "checkout", target])
        print(f"switch to {target}")
    else:
        subprocess.run(["git", "checkout", "-b", target])
        print(f"create {target}")

while_count = 1
shell_cmd = get_shell()
while True:
    print(f"第{while_count}次执行")
    while_count += 1
    fail_count = 0
    
    for cmdStr in commands:
        print(f"running: {cmdStr}")
        result = subprocess.run(shell_cmd + [cmdStr])
        if result.returncode != 0:
            fail_count += 1
        
        # 不自动运行则提示是否继续
        if "auto" not in sys.argv[1:]:
            if input("是否继续？(y/n): ").lower() != 'y':
                sys.exit()
            
    if fail_count == len(commands):
        print("全部执行失败")
        raise SystemExit(1)
