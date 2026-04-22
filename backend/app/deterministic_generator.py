"""
Детерминированный генератор запросов как fallback для GPT.
Гарантирует нужное количество запросов через комбинации и вариации.
"""

import itertools
from typing import List, Dict, Any
from .models import Intent

# Базовые модификаторы для разных интентов
MODIFIERS = {
    "commercial": [
        "купить", "заказать", "приобрести", "цена", "стоимость", "недорого", 
        "дешево", "выгодно", "акция", "скидка", "предложение"
    ],
    "informational": [
        "что такое", "как", "почему", "зачем", "какой", "виды", "типы", 
        "особенности", "характеристики", "свойства", "применение"
    ],
    "service": [
        "услуги", "сервис", "ремонт", "установка", "монтаж", "обслуживание",
        "замена", "настройка", "диагностика", "консультация"
    ],
    "problem": [
        "не работает", "сломался", "проблема", "ошибка", "неисправность",
        "поломка", "дефект", "брак", "починить", "исправить"
    ],
    "price": [
        "цена", "стоимость", "расценки", "тариф", "прайс", "бюджет",
        "сколько стоит", "стоимость услуг", "цены на"
    ]
}

# Синонимы для популярных слов
SYNONYMS = {
    "окна": ["окно", "оконные блоки", "остекление", "оконные конструкции"],
    "ремонт": ["восстановление", "починка", "реставрация", "обновление"],
    "установка": ["монтаж", "установление", "инсталляция", "размещение"],
    "пластиковые": ["ПВХ", "полимерные", "пластик", "винил"],
    "деревянные": ["древесные", "из дерева", "деревоизделия"],
    "стеклопакеты": ["стекло", "остекление", "стеклоблоки"],
    "замена": ["смена", "переустановка", "обновление"],
    "фурнитура": ["комплектующие", "механизмы", "арматура"],
}

def generate_variations(base_query: str, intent: Intent, target_count: int = 15) -> List[str]:
    """Генерирует вариации базового запроса."""
    variations = set()
    words = base_query.lower().split()
    
    # 1. Добавляем базовый запрос
    variations.add(base_query.lower().strip())
    
    # 2. Добавляем модификаторы по интенту
    if intent in MODIFIERS:
        for modifier in MODIFIERS[intent][:5]:  # Берем первые 5
            variations.add(f"{modifier} {base_query}".strip())
            variations.add(f"{base_query} {modifier}".strip())
    
    # 3. Синонимы
    for word in words:
        if word in SYNONYMS:
            for synonym in SYNONYMS[word][:3]:  # Берем первые 3 синонима
                new_query = base_query.replace(word, synonym)
                variations.add(new_query.lower().strip())
    
    # 4. Перестановки слов (для коротких запросов)
    if len(words) <= 3:
        for perm in itertools.permutations(words):
            variations.add(" ".join(perm).strip())
    
    # 5. Добавляем общие префиксы/суффиксы
    general_prefixes = ["как", "где", "какой", "лучший", "качественный"]
    for prefix in general_prefixes[:3]:
        variations.add(f"{prefix} {base_query}".strip())
    
    # 6. Технические вариации
    tech_modifiers = ["профессиональный", "качественный", "надежный", "быстрый"]
    for mod in tech_modifiers[:2]:
        variations.add(f"{mod} {base_query}".strip())
    
    # 7. Если все еще мало - добавляем комбинации
    if len(variations) < target_count:
        base_variations = list(variations)[:5]  # Берем первые 5 как основу
        additional_words = ["услуги", "работы", "мастер", "компания", "цена"]
        
        for base_var in base_variations:
            for add_word in additional_words:
                if len(variations) >= target_count:
                    break
                variations.add(f"{base_var} {add_word}".strip())
                variations.add(f"{add_word} {base_var}".strip())
    
    # Фильтруем и ограничиваем
    result = []
    for var in variations:
        if len(var.split()) >= 2 and len(var.split()) <= 6:  # Длина 2-6 слов
            result.append(var)
        if len(result) >= target_count:
            break
    
    return result[:target_count]

def expand_cluster_deterministic(cluster: Dict[str, Any], target_queries_per_cluster: int = 15) -> Dict[str, Any]:
    """Детерминированно расширяет один кластер."""
    cluster_name = cluster.get("name", "")
    intent_mix = cluster.get("intent_mix", [])
    seed_examples = cluster.get("seed_examples", [])
    
    all_queries = []
    
    # Используем seed_examples как базу
    base_queries = seed_examples if seed_examples else [cluster_name]
    
    # Генерируем для каждого интента
    queries_per_intent = max(1, target_queries_per_cluster // max(len(intent_mix), 1))
    
    for intent in intent_mix:
        for base_query in base_queries[:2]:  # Берем первые 2 базовых запроса
            variations = generate_variations(base_query, intent, queries_per_intent)
            for var in variations:
                if len(all_queries) < target_queries_per_cluster:
                    all_queries.append({
                        "q": var,
                        "intent": intent,
                        "tags": []
                    })
    
    # Если все еще мало - добавляем общие вариации
    while len(all_queries) < target_queries_per_cluster and base_queries:
        for base_query in base_queries:
            if len(all_queries) >= target_queries_per_cluster:
                break
            additional_vars = generate_variations(
                base_query, 
                intent_mix[0] if intent_mix else "informational", 
                target_queries_per_cluster - len(all_queries)
            )
            for var in additional_vars:
                if len(all_queries) < target_queries_per_cluster:
                    all_queries.append({
                        "q": var,
                        "intent": intent_mix[0] if intent_mix else "informational",
                        "tags": []
                    })
    
    return {
        "cluster_id": cluster.get("cluster_id"),
        "cluster_name": cluster.get("name"),
        "queries": all_queries[:target_queries_per_cluster]
    }

def expand_deterministic_fallback(clusters: List[Dict[str, Any]], topic: str, locale: str, target_per_cluster: int = 15) -> Dict[str, Any]:
    """Детерминированный fallback для расширения кластеров."""
    expanded_clusters = []
    
    print(f"Deterministic generator: processing {len(clusters)} clusters with {target_per_cluster} queries each")
    
    for i, cluster in enumerate(clusters):
        print(f"Processing cluster {i+1}/{len(clusters)}: {cluster.get('name', 'Unknown')}")
        
        expanded_cluster = expand_cluster_deterministic(cluster, target_per_cluster)
        expanded_clusters.append(expanded_cluster)
        
        print(f"Generated {len(expanded_cluster['queries'])} queries for cluster {cluster.get('name')}")
    
    total_queries = sum(len(cluster['queries']) for cluster in expanded_clusters)
    print(f"Total generated: {total_queries} queries")
    
    return {
        "topic": topic,
        "locale": locale,
        "expanded": expanded_clusters
    }
