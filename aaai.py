#!/usr/bin/env python3

import subprocess
from time import sleep

branch = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, capture_output=True
).stdout.strip()

target = "refactor-nightly"
commands = [
    fr'''gemini -m gemini-2.5-flash --yolo "读取 .claude\ar3.md 文件里的内容并执行任务"''',
    fr'''codex exec "读取 .claude\ar3.md 文件里的内容并执行任务" -m="gpt-5-codex" --dangerously-bypass-approvals-and-sandbox''',
    fr'''claude --permission-mode bypassPermissions -p "读取 .claude\ar3.md 文件里的内容并执行任务"''',
]

if branch == target:
    print(f"already on {target}")
else:
    exists = subprocess.run(
        ["git", "branch", "--list", target], text=True, capture_output=True
    ).stdout.strip()
    if exists:
        subprocess.run(["git", "checkout", target])
        print(f"switch to {target}")
    else:
        subprocess.run(["git", "checkout", "-b", target])
        print(f"create {target}")

while_count = 1
while True:
    print(f"第{while_count}次执行")
    while_count += 1
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
