#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to fix gpt5_head_queries.py - replace responses.create() with ask_gpt5()
"""
import re

with open('app/gpt5_head_queries.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for the old responses.create block
old_pattern = r'        # Вызываем GPT-5 через Responses API.*?response_text = ""  # Устанавливаем пустую строку для обработки ошибки'

new_code = '''        # Используем новый ask_gpt5() wrapper с нормализацией и обработкой ошибок
        print(f"[GPT5] Model: {OPENAI_MODEL}")
        
        response_text = await ask_gpt5(
            input_blocks=[
                {"role": "user", "content": [{"type": "input_text", "text": prompts["user"]}]}
            ],
            model=OPENAI_MODEL,
            max_output_tokens=12000,
            temperature=0.2,
            reasoning_effort="minimal",
            verbosity="low",
        )
        print("[GPT-5] Response received")
        print(f"[GPT-5] Response length: {len(response_text)} chars")
        print(f"[GPT-5] Response preview: {response_text[:200]}...")'''

content_new = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

if content_new != content:
    with open('app/gpt5_head_queries.py', 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("[OK] Successfully replaced responses.create() with ask_gpt5()")
else:
    print("[ERROR] Pattern not found or already replaced")







