#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Remove openai_client param from function signatures"""
import re

with open('app/gpt5_head_queries.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove openai_client parameter from all function definitions
patterns = [
    (r'def generate_clusters_gpt5_single\(topic: str, selected_intents: List\[str\], target_count: int, openai_client, ', 
     'def generate_clusters_gpt5_single(topic: str, selected_intents: List[str], target_count: int, '),
    
    (r'def generate_clusters_gpt5_expansion\(topic: str, selected_intents: List\[str\], existing_clusters: List\[Dict\[str, Any\]\], target_additional: int, openai_client, ',
     'def generate_clusters_gpt5_expansion(topic: str, selected_intents: List[str], existing_clusters: List[Dict[str, Any]], target_additional: int, '),
    
    (r'def generate_clusters_gpt5\(topic: str, selected_intents: List\[str\], target_count: int, openai_client, ',
     'def generate_clusters_gpt5(topic: str, selected_intents: List[str], target_count: int, '),
    
    (r'def expand_template_with_gpt5\(template, selected_intents: List\[str\], openai_client, ',
     'def expand_template_with_gpt5(template, selected_intents: List[str], '),
]

for old, new in patterns:
    content = re.sub(old, new, content)

# Remove openai_client= from function calls in main.py (also need to fix that)
with open('app/main.py', 'r', encoding='utf-8') as f:
    main_content = f.read()

# Replace function calls
main_content = re.sub(r'await generate_clusters_gpt5\(\s*topic=', 'await generate_clusters_gpt5(\n                topic=', main_content)
main_content = re.sub(r',\s*openai_client=openai_client,', ',', main_content)
main_content = re.sub(r',\s*openai_client=openai_client\)', ',', main_content)

# Save both files
with open('app/gpt5_head_queries.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(main_content)

print("[OK] Removed openai_client parameters from signatures and calls")
