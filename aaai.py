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
        return ["pwsh.exe", "-c"]
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
    fr''' cat .codex/prefix.md .agent/rules/code-style-guide.md | codex exec -m gpt-5.2-codex --dangerously-bypass-approvals-and-sandbox''',
    fr''' cat .codex/prefix.md .agent/rules/code-style-guide.md | gemini --include-directories "D:/work" -y''',
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
    
    for cmdStr in commands:
        print(f"running: {cmdStr}")
        result = subprocess.run(shell_cmd + [cmdStr])
        if result.returncode != 0:
            # 不自动运行则提示是否继续
            if "auto" not in sys.argv[1:]:
                if input("是否继续？(y/n): ").lower() != 'y':
                    sys.exit()
            
