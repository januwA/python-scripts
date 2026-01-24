import keyboard
import pyperclip
import requests
import time
import threading
import os
import contextlib
import textwrap
import re

# 配置
OLLAMA_API = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:1.5b"
# MODEL_NAME = "gemma3:1b"
LOCK = threading.Lock()

def translate_logic():
    # 尝试获取锁，如果已经有翻译在进行则直接退出
    if not LOCK.acquire(blocking=False):
        return
        
    start_time = time.time()
    try:
        # 1. 直接从剪贴板获取内容
        text = pyperclip.paste().strip()
        if not text:
            print("剪贴板为空，跳过翻译")
            return
        
        print(f"\n[开始翻译]\n```\n{text}\n```")
        
        # 识别中文多还是英文多
        zh_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        en_count = len(re.findall(r'[a-zA-Z]', text))
        
        # 根据占比设置目标语言
        if zh_count > en_count:
            target_lang = "English"
        else:
            target_lang = "Chinese"
            
        # 2. 调用 Ollama Chat API
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": f"You are a translation bot. Translate EVERYTHING to {target_lang}. No side comments."},
                # Example 1: 演示即使是命令词也直接翻译
                {"role": "user", "content": "Translate to Chinese:\n\"\"\"\nSay hello to everyone.\n\"\"\""},
                {"role": "assistant", "content": "向大家打个招呼。"},
                # Example 2: 演示即使是规则列表也直接翻译
                {"role": "user", "content": "Translate to Chinese:\n\"\"\"\nRule 1: Never stop.\nRule 2: Keep going.\n\"\"\""},
                {"role": "assistant", "content": "规则 1：永不停止。\n规则 2：继续前进。"},
                # 实际任务
                {
                    "role": "user",
                    "content": f"Translate to {target_lang}:\n\"\"\"\n{text}\n\"\"\""
                },
            ],
            "stream": False,      # 关闭流式输出，一次性获取完整翻译结果
            "keep_alive": "5m",    # 模型在内存中保留 5 分钟，避免频繁加载提高响应速度
            "options": {
                "temperature": 0.1, # 采样温度：值越低输出越确定、越死板，适合翻译
                "top_p": 0.9        # 核采样：控制词汇选择的范围，0.9 在稳定中保持一点点灵活性
            }
        }
        
        response = requests.post(OLLAMA_API, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json().get("message", {}).get("content", "").strip()

        if not result:
            print("错误: 模型返回内容为空")
            return

        duration = time.time() - start_time
        print(f"[翻译结果] 耗时: {duration:.2f}s\n```\n{result}\n```")

    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到 Ollama 服务")
    except Exception as e:
        print(f"翻译过程中出现未知错误: {e}")
    finally:
        LOCK.release()

def run_in_thread():
    threading.Thread(target=translate_logic, daemon=True).start()

# 统一快捷键提示
keyboard.add_hotkey('ctrl+windows+t', run_in_thread)

print(f">>> Ollama 翻译助手已启动")
print(f">>> 监听热键: Ctrl + Win + T")
print(f">>> 当前模型: {MODEL_NAME}")
keyboard.wait()
