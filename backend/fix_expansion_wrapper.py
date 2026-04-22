#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to fix generate_clusters_gpt5_expansion - replace responses.create() with ask_gpt5()
"""
import re

with open('app/gpt5_head_queries.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for the old responses.create block in expansion function
old_pattern = r'    try:\n        response = await openai_client\.responses\.create\(\n            model="gpt-5",\n            max_output_tokens=8000,\n            input=\[\{"role": "user", "content": \[\{"type": "input_text", "text": expansion_prompt\}\]\}\],\n        \)\n        \n        response_text = response\.output_text'

new_code = '''    try:
        response_text = await ask_gpt5(
            input_blocks=[
                {"role": "user", "content": [{"type": "input_text", "text": expansion_prompt}]}
            ],
            model=OPENAI_MODEL,
            max_output_tokens=8000,
            temperature=0.2,
            reasoning_effort="minimal",
            verbosity="low",
        )'''

content_new = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

if content_new != content:
    with open('app/gpt5_head_queries.py', 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("[OK] Successfully replaced expansion responses.create() with ask_gpt5()")
else:
    print("[ERROR] Pattern not found or already replaced")







