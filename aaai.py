#!/usr/bin/env python3

import subprocess
from time import sleep

branch = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, capture_output=True, check=True
).stdout.strip()

target = "refactor-nightly"
commands = [
    fr'''cat C:\Users\16418\.claude\commands\aja\ar.md | gemini -m gemini-2.5-flash --yolo''',
    fr'''codex exec "读取 C:\Users\16418\.claude\commands\aja\ar.md 文件里的内容并执行任务" -m="gpt-5-code" --dangerously-bypass-approvals-and-sandbox''',
    fr'''cat C:\Users\16418\.claude\commands\aja\ar.md | claude --permission-mode bypassPermissions -p''',
]

if branch == target:
    print(f"already on {target}")
else:
    exists = subprocess.run(
        ["git", "branch", "--list", target], text=True, capture_output=True, check=True
    ).stdout.strip()
    if exists:
        subprocess.run(["git", "checkout", target], check=True)
        print(f"switch to {target}")
    else:
        subprocess.run(["git", "checkout", "-b", target], check=True)
        print(f"create {target}")

while True:
    fail_count = 0
    
    for cmd in commands:
        print(f"running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            fail_count += 1
        sleep(10)
            
    if fail_count == len(commands):
        print("全部执行失败")
        raise SystemExit(1)
