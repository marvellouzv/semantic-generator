"""
Нормализация и дедупликация head-запросов для улучшения качества результатов GPT-5.
"""

import re
from typing import List, Dict, Any, Set
from collections import defaultdict

def normalize_query(query: str) -> str:
    """
    Нормализует запрос для дедупликации.
    
    Args:
        query: Исходный запрос
        
    Returns:
        Нормализованный запрос
    """
    if not query:
        return ""
    
    # Приводим к нижнему регистру и убираем лишние пробелы
    s = query.strip().lower()
    
    # Заменяем ё на е
    s = s.replace("ё", "е")
    
    # Нормализуем множественные пробелы
    s = re.sub(r'\s+', ' ', s)
    
    # Убираем знаки препинания в конце
    s = s.rstrip('.,!?;:')
    
    # Нормализуем окончания для русского языка (эвристика)
    # -ирование/-ирования -> -ирование
    s = re.sub(r'(ировани)(е|я)$', r'ирование', s)
    
    # -ание/-ания -> -ание
    s = re.sub(r'(ан|ян)(ие|ия)$', r'ание', s)
    
    # -ение/-ения -> -ение
    s = re.sub(r'(ен)(ие|ия)$', r'ение', s)
    
    # Множественное/единственное число (простая эвристика)
    # окна -> окно, услуги -> услуга
    s = re.sub(r'окна$', 'окно', s)
    s = re.sub(r'услуги$', 'услуга', s)
    s = re.sub(r'цены$', 'цена', s)
    s = re.sub(r'работы$', 'работа', s)
    s = re.sub(r'компании$', 'компания', s)
    
    return s

def extract_root_word(query: str) -> str:
    """
    Извлекает корневое слово из запроса для проверки разнообразия.
    
    Args:
        query: Запрос
        
    Returns:
        Предполагаемое корневое слово
    """
    if not query:
        return ""
    
    words = query.lower().split()
    if not words:
        return ""
    
    # Берем первое значимое слово (не предлог/союз)
    stop_words = {'в', 'на', 'по', 'для', 'от', 'до', 'с', 'без', 'под', 'над', 'при', 'о', 'об'}
    
    for word in words:
        if word not in stop_words and len(word) > 2:
            # Простая лемматизация (убираем распространенные окончания)
            root = word
            
            # Убираем окончания
            for ending in ['ение', 'ание', 'ирование', 'ость', 'ный', 'ной', 'ский', 'цкий']:
                if root.endswith(ending) and len(root) > len(ending) + 2:
                    root = root[:-len(ending)]
                    break
            
            return root
    
    return words[0] if words else ""

def deduplicate_queries(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Дедуплицирует запросы внутри и между кластерами.
    
    Args:
        clusters: Список кластеров с запросами
        
    Returns:
        Кластеры с дедуплицированными запросами
    """
    
    # Глобальный набор нормализованных запросов
    global_seen = set()
    
    # Статистика
    original_count = 0
    final_count = 0
    
    result_clusters = []
    
    for cluster in clusters:
        cluster_name = cluster.get("name", "")
        original_count += 1
        
        # Нормализуем название кластера
        normalized_name = normalize_query(cluster_name)
        
        # Проверяем, не встречался ли уже такой кластер
        if normalized_name in global_seen:
            print(f"Skipping duplicate cluster: {cluster_name}")
            continue
        
        global_seen.add(normalized_name)
        result_clusters.append(cluster)
        final_count += 1
    
    print(f"Deduplication: {original_count} -> {final_count} clusters")
    return result_clusters

def check_diversity_within_theme(queries: List[str], theme_name: str) -> List[str]:
    """
    Проверяет разнообразие запросов внутри одной темы.
    
    Args:
        queries: Список запросов в теме
        theme_name: Название темы
        
    Returns:
        Отфильтрованный список запросов с улучшенным разнообразием
    """
    
    if len(queries) <= 3:
        return queries
    
    # Группируем по корневым словам
    root_groups = defaultdict(list)
    
    for query in queries:
        root = extract_root_word(query)
        root_groups[root].append(query)
    
    # Если слишком много запросов с одним корнем, оставляем только лучшие
    result = []
    
    for root, group_queries in root_groups.items():
        if len(group_queries) > 3:
            # Оставляем только 2-3 самых коротких (обычно более общих)
            sorted_queries = sorted(group_queries, key=len)
            result.extend(sorted_queries[:3])
            print(f"Theme '{theme_name}': reduced {len(group_queries)} queries with root '{root}' to 3")
        else:
            result.extend(group_queries)
    
    return result

def enhance_cluster_diversity(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Улучшает разнообразие кластеров, применяя Diversity Guards.
    
    Args:
        clusters: Исходные кластеры
        
    Returns:
        Кластеры с улучшенным разнообразием
    """
    
    enhanced_clusters = []
    
    for cluster in clusters:
        cluster_name = cluster.get("name", "")
        seed_examples = cluster.get("seed_examples", [cluster_name])
        parent_theme = cluster.get("notes", "").replace("Parent Theme: ", "").split(",")[0]
        
        # Улучшаем разнообразие примеров внутри кластера
        if seed_examples:
            diverse_examples = check_diversity_within_theme(seed_examples, parent_theme)
            cluster["seed_examples"] = diverse_examples
        
        enhanced_clusters.append(cluster)
    
    return enhanced_clusters

def normalize_and_deduplicate_clusters(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Основная функция нормализации и дедупликации кластеров.
    
    Args:
        clusters: Исходные кластеры от GPT-5
        
    Returns:
        Нормализованные и дедуплицированные кластеры
    """
    
    print(f"Starting normalization and deduplication for {len(clusters)} clusters")
    
    # Шаг 1: Дедупликация
    deduped_clusters = deduplicate_queries(clusters)
    
    # Шаг 2: Улучшение разнообразия
    enhanced_clusters = enhance_cluster_diversity(deduped_clusters)
    
    print(f"Normalization complete: {len(enhanced_clusters)} final clusters")
    
    return enhanced_clusters
