# llm_stage2.py
import os
import json
from typing import List, Dict, Literal, Tuple
from dotenv import load_dotenv
from .gpt5_wrapper import ask_gpt5

load_dotenv()

PRIMARY_MODEL = os.getenv("OPENAI_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1"))
FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", os.getenv("OPENROUTER_FALLBACK_MODEL", "openai/gpt-5-mini"))

Intent = Literal["commercial","transactional","informational","navigational"]

# Chat completions removed; we always use Responses API via ask_gpt5()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "QueryExpansion",
        "schema": {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "head_query": {"type": "string"},
                            "intent": {"type": "string", "enum": ["commercial","transactional","informational","navigational"]},
                            "demand": {"type": "string", "enum": ["High","Medium","Low"]},
                            "parent_theme": {"type": "string"}
                        },
                        "required": ["head_query","intent","demand","parent_theme"],
                        "additionalProperties": False
                    },
                    "minItems": 8,
                    "maxItems": 20
                }
            },
            "required": ["rows"],
            "additionalProperties": False
        },
        "strict": True
    }
}

SYSTEM = (
    "You are a senior Russian-market SEO strategist (Google RU + Яндекс). "
    "Expand only with NEW head queries (1–3 words, rarely 4). "
    "No long tails. For local queries, follow region constraints from the prompt. "
    "Deduplicate vs provided list by lemma/meaning. Normalize to one canonical form. "
    "Return JSON per provided schema. No explanations."
)

def _load_system_step2_prompt() -> str:
    """
    Load the static Stage 2 expansion prompt from prompts/system_step2.md.
    Falls back to SYSTEM if the file is missing.
    """
    path = os.path.join(PROMPT_DIR, "system_step2.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return SYSTEM

SYSTEM_STEP2_PROMPT = _load_system_step2_prompt()


def _build_region_variants(regions: List[str]) -> Dict[str, List[str]]:
    canonical = [r.strip() for r in (regions or []) if r and r.strip()]
    out: Dict[str, List[str]] = {}
    curated: Dict[str, List[str]] = {
        "санкт-петербург": ["санкт-петербург", "санкт петербург", "спб", "питер", "петербург", "в спб", "в питере", "в санкт петербурге", "в петербурге"],
        "санкт петербург": ["санкт-петербург", "санкт петербург", "спб", "питер", "петербург", "в спб", "в питере", "в санкт петербурге", "в петербурге"],
        "москва": ["москва", "мск", "в москве"],
        "московская область": ["московская область", "подмосковье", "в московской области", "в подмосковье"],
        "екатеринбург": ["екатеринбург", "екб", "в екатеринбурге"],
        "новосибирск": ["новосибирск", "нск", "в новосибирске"],
        "нижний новгород": ["нижний новгород", "нн", "в нижнем новгороде"],
        "казань": ["казань", "в казани"],
        "краснодар": ["краснодар", "в краснодаре"],
    }
    for r in canonical:
        key = r.lower()
        variants = curated.get(key) or [r, f"в {r}"]
        seen = set()
        uniq: List[str] = []
        for v in variants:
            vv = v.strip()
            if not vv:
                continue
            low = vv.lower()
            if low in seen:
                continue
            seen.add(low)
            uniq.append(vv)
        out[r] = uniq
    return out

def build_user_prompt(
    topic: str,
    allowed_types_csv: str,
    user_notes: str,
    parent_themes: List[str],
    existing_by_parent: Dict[str, List[str]],
    target_count: int,
    minus_words: List[str] | None = None,
    regions: List[str] | None = None,
    local_allowed: bool = False,
) -> str:
    parents_block = "\n".join(f"- {p}" for p in parent_themes)
    existing_block = "\n".join(
        [f"# {p}: " + "; ".join(f"\"{h}\"" for h in heads) for p, heads in existing_by_parent.items()]
    )
    minus_words_clean = [w.strip() for w in (minus_words or []) if w and w.strip()]
    minus_block = ""
    if minus_words_clean:
        minus_block = "NEGATIVE WORDS (STRICT):\n" + "\n".join([f"- {w}" for w in minus_words_clean]) + "\n"

    region_block = ""
    if local_allowed and regions:
        region_map = _build_region_variants(regions)
        if region_map:
            lines = [f"- {reg}: {', '.join(vars_)}" for reg, vars_ in region_map.items()]
            region_block = (
                "REGION RULES FOR LOCAL QUERIES (STRICT):\n"
                "Local queries MUST be ONLY for these regions and MUST include exactly ONE allowed region variant.\n"
                "Do NOT use any other cities/regions.\n"
                + "\n".join(lines)
                + "\n"
            )

    local_rules = ""
    if local_allowed:
        if regions:
            local_rules = "LOCAL RULE: regions are specified -> local queries must include allowed region variants only (see REGION RULES).\n"
        else:
            local_rules = "LOCAL RULE: regions are NOT specified -> do NOT use explicit city names (use 'рядом', 'в городе', etc.).\n"

    return (
        f'TOPIC: "{topic}"\n'
        f"ALLOWED TYPES: {allowed_types_csv}\n"
        f"USER ADDITIONAL REQUIREMENTS: {user_notes}\n\n"
        f"{minus_block}{region_block}{local_rules}\n"
        f"PARENT THEMES (existing):\n{parents_block}\n\n"
        f"EXISTING HEAD QUERIES (DO NOT DUPLICATE):\n{existing_block}\n\n"
        f"TARGET: Generate {target_count} NEW high-quality head queries\n\n"
        "TASK:\n"
        f"1. Focus on the USER ADDITIONAL REQUIREMENTS: \"{user_notes}\"\n"
        "2. Generate NEW natural search queries (2-7 words) in Russian\n"
        "3. Each query MUST be related to the topic and match ALLOWED TYPES\n"
        "4. Create diverse queries that cover different aspects of the user's request\n"
        "5. Distribute queries across existing Parent Themes OR create new relevant themes\n"
        "6. NO parentheses, slashes, or special symbols - only natural queries\n"
        "7. STRICTLY avoid duplicates with EXISTING HEAD QUERIES\n\n"
        "QUALITY REQUIREMENTS:\n"
        "- Natural queries as real users would type them\n"
        f"- Each query must contain topic-specific words related to \"{topic}\"\n"
        f"- Focus on the user's specific request: \"{user_notes}\"\n"
        "- Prefer concrete, actionable queries over generic ones\n\n"
        "Return ONLY a JSON object with format: {rows:[{head_query, intent, demand, parent_theme}]}"
    )

async def call_stage2_json(system: str, user: str, model: str = PRIMARY_MODEL, max_out: int = 1600) -> Dict:
    """
    Call Responses API and return parsed JSON dict.
    Now fully async - no run_until_complete.
    """
    print(f"[LLM_Stage2] Calling {model} with {max_out} max_output_tokens (Responses API)")
    
    # Keep full context as separate system + user blocks.
    # Request JSON format in prompt since response_format is not supported by Responses API.
    user_with_json_guard = (
        user
        + "\n\nReturn ONLY a valid JSON object with format: {rows:[{head_query, intent, demand, parent_theme}]}\n"
        + "No markdown, no explanations, just the JSON."
    )
    
    # Direct async call
    # Note: Responses API does not support temperature parameter
    response_text = await ask_gpt5(
        input_blocks=[
            {"role": "system", "content": [{"type": "input_text", "text": system}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_with_json_guard}]},
        ],
        model=model,
        max_output_tokens=max_out,
    )
    
    text = response_text or ""
    
    if not text.strip():
        print(f"[LLM_Stage2] Empty response text, raising error")
        raise RuntimeError("Stage2: empty response text — increase max_output_tokens or reduce target_count.")
    
    print(f"[LLM_Stage2] Response text preview: {text[:200]}...")
    
    # Clean markdown blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    print(f"[LLM_Stage2] Cleaned text preview: {text[:200]}...")
    
    try:
        data = json.loads(text)
        print(f"[LLM_Stage2] Successfully parsed JSON with {len(data.get('rows', []))} rows")
        return data
    except json.JSONDecodeError as e:
        print(f"[LLM_Stage2] JSON parsing error: {e}")
        print(f"[LLM_Stage2] Raw text: {text}")
        raise RuntimeError(f"Stage2: invalid JSON response - {e}")

async def expand_stage2(
    topic: str,
    allowed_types: List[str],
    user_notes: str,
    parent_themes: List[str],
    existing_by_parent: Dict[str, List[str]],
    target_count: int,
    minus_words: List[str] | None = None,
    regions: List[str] | None = None,
) -> List[Dict]:
    """
    Expand queries in Stage 2. Now fully async.
    Tries primary model first, then fallback model.
    Only Responses API - no legacy fallbacks.
    """
    allowed_map = {
        "commercial": "commercial",
        "informational": "informational",
        "service": "transactional",   # маппинг из UI
        "price": "commercial",
        "local": "navigational",
        "transactional": "transactional",
        "navigational": "navigational",
    }
    # подготавливаем ALLOWED TYPES для промпта
    intents = []
    for t in allowed_types:
        v = allowed_map.get(t, None)
        if v and v not in intents:
            intents.append(v)
    allowed_types_csv = ", ".join(intents) if intents else "commercial, informational, transactional, navigational"

    user = build_user_prompt(
        topic=topic,
        allowed_types_csv=allowed_types_csv,
        user_notes=user_notes,
        parent_themes=parent_themes,
        existing_by_parent=existing_by_parent,
        target_count=target_count,
        minus_words=minus_words,
        regions=regions,
        local_allowed=("local" in allowed_types),
    )

    # 1) Try primary model
    data = None
    last_error = None
    
    try:
        print(f"[LLM_Stage2] Trying primary model: {PRIMARY_MODEL}...")
        # Increased max_output_tokens for more queries
        data = await call_stage2_json(SYSTEM_STEP2_PROMPT, user, model=PRIMARY_MODEL, max_out=4000)
    except Exception as e:
        print(f"[LLM_Stage2] Primary model failed: {e}")
        last_error = e
        
        # 2) Fallback model
        try:
            print(f"[LLM_Stage2] Trying fallback model: {FALLBACK_MODEL}...")
            data = await call_stage2_json(SYSTEM_STEP2_PROMPT, user, model=FALLBACK_MODEL, max_out=3000)
        except Exception as e2:
            print(f"[LLM_Stage2] Fallback model failed: {e2}")
            last_error = e2
    
    # If both failed, raise the last error
    if data is None:
        raise RuntimeError(f"Stage2: All models failed. Last error: {last_error}")

    rows = data.get("rows", [])
    # Light validation and deduplication
    out = []
    seen = set()
    for r in rows:
        h = r.get("head_query", "").strip()
        it = r.get("intent", "").strip()
        dm = r.get("demand", "").strip()
        pt = r.get("parent_theme", "").strip()
        if not (h and it and dm and pt): 
            continue
        key = (h.lower(), it, dm, pt.lower())
        if key in seen: 
            continue
        seen.add(key)
        out.append({"Head Query": h, "Intent": it, "Demand Level": dm, "Parent Theme": pt})
    
    print(f"[LLM_Stage2] Returning {len(out)} validated queries")
    return out
