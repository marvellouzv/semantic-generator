from __future__ import annotations
import re, itertools
from typing import Dict, Any, List
from rapidfuzz import fuzz
from razdel import tokenize as rz_tokenize
from pymorphy3 import MorphAnalyzer

morph = MorphAnalyzer()

def _norm_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def _lemmas(s: str) -> str:
    tokens = [t.text for t in rz_tokenize(s)]
    lem = []
    for t in tokens:
        if len(t) <= 2:  # simple stop
            continue
        p = morph.parse(t)[0]
        lem.append(p.normal_form)
    return " ".join(lem)

def _dedup(queries: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    seen_lemmas = set()
    for q in queries:
        qn = _norm_text(q)
        if qn in seen: 
            continue
        lem = _lemmas(qn)
        if lem in seen_lemmas:
            continue
        # fuzzy pass vs last 200 to keep O(n^2) down
        compare_pool = out[-200:]
        is_dup = False
        for other in compare_pool:
            r = fuzz.token_set_ratio(qn, other)
            if r >= 95:
                is_dup = True
                break
        if not is_dup:
            out.append(qn)
            seen.add(qn)
            seen_lemmas.add(lem)
    return out

def _is_garbage(q: str) -> bool:
    # Убираем ограничения на длину - нужны СЧ и НЧ запросы
    if len(q.strip()) < 3:  # Минимум 3 символа
        return True
    
    # Фильтруем явно мусорные запросы
    garbage_patterns = [
        r"чернильный тест",  # Не относится к тематике
        r"не закрываться$",  # Неполные фразы
        r"^[а-я]{1,2}$",     # Очень короткие слова
        r"(бесплатно\s+бесплатно|купить\s+купить)",  # Повторы
        r"^\d+$",            # Только цифры
        r"^[^а-яё\s]+$",     # Только латиница/символы
    ]
    
    for pattern in garbage_patterns:
        if re.search(pattern, q, re.IGNORECASE):
            return True
    
    return False

def _generate_tags(query: str, intent: str) -> List[str]:
    """Generate semantic tags for a query based on its properties."""
    tags = []
    q_lower = query.lower()
    words = q_lower.split()
    
    # 1. Длина запроса
    if len(words) <= 2:
        tags.append("короткий")
    elif len(words) <= 4:
        tags.append("средний")
    else:
        tags.append("длинный")
    
    # 2. Тип действия
    action_words = [
        (["купить", "заказать", "приобрести"], "покупка"),
        (["что", "как", "почему", "какой"], "информация"), 
        (["сравнить", "vs", "или", "лучше"], "сравнение"),
        (["не работает", "сломался", "проблема", "ошибка"], "проблема")
    ]
    for words_list, tag in action_words:
        if any(word in q_lower for word in words_list):
            tags.append(tag)
            break
    
    # 3. Географичность
    geo_words = ["москва", "спб", "город", "район", "рядом", "недалеко", "местный"]
    if any(word in q_lower for word in geo_words):
        tags.append("локальный")
    else:
        tags.append("общий")
    
    # 4. Сезонность
    seasonal_words = ["зимой", "летом", "сезон", "холод", "тепло", "осень", "весна"]
    if any(word in q_lower for word in seasonal_words):
        tags.append("сезонный")
    else:
        tags.append("всесезонный")
    
    # 5. Сложность
    complex_words = ["профессиональный", "технический", "установка", "монтаж", "система"]
    simple_words = ["простой", "быстро", "легко", "дешево"]
    if any(word in q_lower for word in complex_words):
        tags.append("сложный")
    elif any(word in q_lower for word in simple_words):
        tags.append("простой")
    else:
        tags.append("средняя_сложность")
    
    # 6. Срочность
    urgent_words = ["срочно", "быстро", "сегодня", "немедленно", "экстренно"]
    if any(word in q_lower for word in urgent_words):
        tags.append("срочный")
    else:
        tags.append("плановый")
    
    # 7. Бюджет
    budget_words = [
        (["дешево", "недорого", "бюджет", "эконом"], "дешевый"),
        (["дорого", "премиум", "элитный", "люкс"], "премиум"),
        (["цена", "стоимость", "расценки"], "средний_бюджет")
    ]
    for words_list, tag in budget_words:
        if any(word in q_lower for word in words_list):
            tags.append(tag)
            break
    
    # 8. Целевая аудитория
    if any(word in q_lower for word in ["офис", "компания", "бизнес", "организация"]):
        tags.append("бизнес")
    elif any(word in q_lower for word in ["дом", "квартира", "личный", "семья"]):
        tags.append("частные_лица")
    else:
        tags.append("универсальный")
    
    # 9. Стадия воронки (по интенту)
    funnel_mapping = {
        "informational": "осознание",
        "comparative": "рассмотрение", 
        "commercial": "покупка",
        "service": "послепродажа",
        "problem": "послепродажа"
    }
    if intent in funnel_mapping:
        tags.append(funnel_mapping[intent])
    
    # 10. Эмоциональность
    emotional_words = ["проблема", "сломался", "не работает", "помогите", "срочно", "ужасно"]
    if any(word in q_lower for word in emotional_words):
        tags.append("эмоциональный")
    else:
        tags.append("нейтральный")
    
    return list(set(tags))  # Remove duplicates

def postprocess_expanded(result: Dict[str, Any], max_total: int = 2000) -> Dict[str, Any]:
    expanded = result.get("expanded", [])
    all_items: List[tuple[int, int, str]] = []  # (cluster_idx, query_idx, text)
    for ci, c in enumerate(expanded):
        for qi, item in enumerate(c.get("queries", [])):
            q = item.get("q", "")
            if not q:
                continue
            if _is_garbage(q):
                continue
            all_items.append((ci, qi, _norm_text(q)))

    print(f"[Postprocess] Raw queries before dedup: {len(all_items)}")
    
    # deduplicate globally
    deduped_texts = _dedup([x[2] for x in all_items])
    print(f"[Postprocess] After deduplication: {len(deduped_texts)}")
    
    # Truncate to max_total softly
    deduped_texts = deduped_texts[:max_total]
    print(f"[Postprocess] After truncation to {max_total}: {len(deduped_texts)}")

    # Rebuild structure, preserving cluster grouping where possible
    text_set = set(deduped_texts)
    new_expanded = []
    for c in expanded:
        new_q = []
        for it in c.get("queries", []):
            q = _norm_text(it.get("q",""))
            if q in text_set:
                # Generate tags for the query
                original_q = it.get("q", "")
                intent = it.get("intent", "")
                generated_tags = _generate_tags(original_q, intent)
                
                # Merge with existing tags
                existing_tags = it.get("tags", [])
                all_tags = list(set(existing_tags + generated_tags))
                
                # Update query with tags
                updated_item = {**it, "tags": all_tags}
                new_q.append(updated_item)
                text_set.remove(q)
        if new_q:
            new_expanded.append({"cluster_id": c["cluster_id"], "cluster_name": c["cluster_name"], "queries": new_q})

    result["expanded"] = new_expanded
    
    # Подсчитываем финальное количество запросов
    final_count = sum(len(c.get("queries", [])) for c in new_expanded)
    print(f"[Postprocess] Final result: {final_count} queries in {len(new_expanded)} clusters")
    
    return result
