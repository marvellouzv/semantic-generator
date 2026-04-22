# -*- coding: utf-8 -*-
"""
Batch generation for long-form semantic queries.
Splits large generation tasks into batches to avoid timeouts.

Strategy:
- Generate 200-300 lines per batch (NDJSON format)
- Each batch: 2000-4000 max_output_tokens
- Run 3-6 batches in parallel (semaphore-controlled)
- Merge, normalize, and deduplicate results
"""
from __future__ import annotations
import asyncio
import logging
import re
from typing import List, Set, Dict, Any
from .gpt5_wrapper import ask_gpt5

log = logging.getLogger("llm")

# Constants for batching
LINES_PER_BATCH = 250  # Target lines per batch
MAX_OUTPUT_TOKENS_PER_BATCH = 3000  # Max tokens per batch
MAX_PARALLEL_BATCHES = 5  # Max concurrent requests


def normalize_query(query: str) -> str:
    """
    Normalize a query: lowercase, strip, remove extra spaces.
    """
    return re.sub(r'\s+', ' ', query.strip().lower())


def deduplicate_queries(queries: List[str]) -> List[str]:
    """
    Deduplicate queries:
    1. Exact match (case-insensitive)
    2. TODO: Lemmatization-based dedup (future enhancement)
    3. TODO: Fuzzy dedup (future enhancement)
    
    Returns:
        Deduplicated list of queries
    """
    seen: Set[str] = set()
    result: List[str] = []
    
    for query in queries:
        normalized = normalize_query(query)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(query.strip())  # Keep original case
    
    return result


async def generate_batch(
    prompt: str,
    batch_num: int,
    total_batches: int,
    lines_target: int,
    model: str = "gpt-5",
) -> List[str]:
    """
    Generate one batch of semantic queries.
    
    Args:
        prompt: Full generation prompt
        batch_num: Current batch number (0-indexed)
        total_batches: Total number of batches
        lines_target: Target number of lines for this batch
        model: Model to use
        
    Returns:
        List of generated queries (one per line)
    """
    batch_prompt = f"""{prompt}

BATCH INFO:
- This is batch {batch_num + 1} of {total_batches}
- Generate approximately {lines_target} unique queries for this batch
- Output format: NDJSON (one query per line, NO numbering, NO comments)
- DO NOT repeat queries from previous batches
- Focus on diversity and coverage

Generate {lines_target} queries now (one per line):"""
    
    try:
        log.info(
            "[BATCH] Generating batch %d/%d (target: %d lines, max_output_tokens: %d)",
            batch_num + 1,
            total_batches,
            lines_target,
            MAX_OUTPUT_TOKENS_PER_BATCH
        )
        
        response_text = await ask_gpt5(
            input_blocks=[{
                "role": "user",
                "content": [{"type": "input_text", "text": batch_prompt}]
            }],
            model=model,
            max_output_tokens=MAX_OUTPUT_TOKENS_PER_BATCH,
        )
        
        # Parse NDJSON: split by newlines, filter empty
        lines = [
            line.strip()
            for line in response_text.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]
        
        # Remove numbering if present (e.g., "1. query" -> "query")
        cleaned_lines = []
        for line in lines:
            # Remove leading numbers and dots
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
            if cleaned:
                cleaned_lines.append(cleaned)
        
        log.info(
            "[BATCH] Batch %d/%d completed: %d queries generated",
            batch_num + 1,
            total_batches,
            len(cleaned_lines)
        )
        
        return cleaned_lines
        
    except Exception as e:
        log.error(
            "[BATCH] Batch %d/%d failed: %s",
            batch_num + 1,
            total_batches,
            str(e)
        )
        # Return empty list on failure - don't fail entire generation
        return []


async def generate_large_query_set(
    topic: str,
    intents: List[str],
    geo: str = "",
    target_count: int = 1500,
    model: str = "gpt-5",
) -> List[str]:
    """
    Generate a large set of semantic queries using batching strategy.
    
    Args:
        topic: Topic/theme for generation
        intents: List of allowed intents
        geo: Geographic modifier (optional)
        target_count: Target number of unique queries
        model: Model to use
        
    Returns:
        List of unique queries
    """
    # Calculate batching parameters
    num_batches = max(1, (target_count + LINES_PER_BATCH - 1) // LINES_PER_BATCH)
    lines_per_batch = (target_count + num_batches - 1) // num_batches
    
    log.info(
        "[BATCH] Starting large generation: target=%d, batches=%d, lines_per_batch=%d",
        target_count,
        num_batches,
        lines_per_batch
    )
    
    # Build base prompt
    intents_str = ", ".join(intents)
    geo_str = f" ({geo})" if geo else ""
    
    base_prompt = f"""Generate diverse semantic search queries for the topic: "{topic}"{geo_str}

REQUIREMENTS:
1. Output format: NDJSON (one query per line, NO numbering, NO comments, NO markdown)
2. Query length: 2-7 words (natural search queries)
3. Intents to cover: {intents_str}
4. Language: Russian
5. Diversity: Cover all aspects of the topic
6. NO duplicate queries
7. NO parentheses, slashes, or special symbols

EXAMPLES (format only):
купить {topic}
{topic} цена
как выбрать {topic}
лучший {topic}
{topic} отзывы"""
    
    # Create semaphore to limit parallel requests
    semaphore = asyncio.Semaphore(MAX_PARALLEL_BATCHES)
    
    async def generate_with_semaphore(batch_num: int) -> List[str]:
        async with semaphore:
            return await generate_batch(
                prompt=base_prompt,
                batch_num=batch_num,
                total_batches=num_batches,
                lines_target=lines_per_batch,
                model=model
            )
    
    # Generate all batches in parallel (with semaphore limiting concurrency)
    tasks = [generate_with_semaphore(i) for i in range(num_batches)]
    batch_results = await asyncio.gather(*tasks)
    
    # Merge all batches
    all_queries: List[str] = []
    for batch_queries in batch_results:
        all_queries.extend(batch_queries)
    
    log.info(
        "[BATCH] All batches completed: %d raw queries generated",
        len(all_queries)
    )
    
    # Deduplicate
    unique_queries = deduplicate_queries(all_queries)
    
    log.info(
        "[BATCH] After deduplication: %d unique queries (%.1f%% unique)",
        len(unique_queries),
        100.0 * len(unique_queries) / len(all_queries) if all_queries else 0
    )
    
    return unique_queries


# Example usage
if __name__ == "__main__":
    async def test_batch():
        queries = await generate_large_query_set(
            topic="холодильники",
            intents=["commercial", "informational", "service", "price"],
            target_count=500
        )
        print(f"Generated {len(queries)} queries")
        print("Sample queries:")
        for q in queries[:10]:
            print(f"  - {q}")
    
    asyncio.run(test_batch())

