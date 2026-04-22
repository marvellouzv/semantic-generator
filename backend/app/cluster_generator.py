"""
Детерминированный генератор кластеров для гарантированного количества.
"""

from typing import List, Dict, Any
from .models import Intent

def generate_clusters_deterministic(topic: str, intents: List[Intent], target_count: int = 50) -> List[Dict[str, Any]]:
    """Генерирует кластеры детерминированно для гарантированного количества."""
    
    clusters = []
    base_topic = topic.lower()
    
    # Базовые шаблоны кластеров для разных тематик
    cluster_templates = {
        # Основные категории (всегда применимы)
        "basic": [
            {"name": f"{topic}", "intents": ["informational", "commercial"]},
            {"name": f"Виды {topic.lower()}", "intents": ["informational"]},
            {"name": f"Типы {topic.lower()}", "intents": ["informational"]},
            {"name": f"Услуги по {topic.lower()}", "intents": ["service", "commercial"]},
            {"name": f"Цены на {topic.lower()}", "intents": ["price", "commercial"]},
            {"name": f"Стоимость {topic.lower()}", "intents": ["price"]},
            {"name": f"Заказать {topic.lower()}", "intents": ["commercial"]},
            {"name": f"Купить {topic.lower()}", "intents": ["commercial"]},
            {"name": f"Как выбрать {topic.lower()}", "intents": ["informational"]},
            {"name": f"Лучший {topic.lower()}", "intents": ["comparative", "informational"]},
        ],
        
        # Проблемы и решения
        "problems": [
            {"name": f"Проблемы с {topic.lower()}", "intents": ["problem", "informational"]},
            {"name": f"Не работает {topic.lower()}", "intents": ["problem"]},
            {"name": f"Сломался {topic.lower()}", "intents": ["problem"]},
            {"name": f"Ремонт {topic.lower()}", "intents": ["service", "commercial"]},
            {"name": f"Восстановление {topic.lower()}", "intents": ["service"]},
            {"name": f"Замена {topic.lower()}", "intents": ["service", "commercial"]},
            {"name": f"Обслуживание {topic.lower()}", "intents": ["service"]},
            {"name": f"Диагностика {topic.lower()}", "intents": ["service", "informational"]},
            {"name": f"Профилактика {topic.lower()}", "intents": ["service", "informational"]},
            {"name": f"Устранение неисправностей {topic.lower()}", "intents": ["service", "problem"]},
        ],
        
        # Материалы и компоненты
        "materials": [
            {"name": f"Материалы для {topic.lower()}", "intents": ["informational", "commercial"]},
            {"name": f"Комплектующие {topic.lower()}", "intents": ["commercial", "informational"]},
            {"name": f"Запчасти для {topic.lower()}", "intents": ["commercial"]},
            {"name": f"Инструменты для {topic.lower()}", "intents": ["commercial", "diy"]},
            {"name": f"Оборудование для {topic.lower()}", "intents": ["commercial", "informational"]},
            {"name": f"Технологии {topic.lower()}", "intents": ["informational", "technical"]},
            {"name": f"Качество {topic.lower()}", "intents": ["informational", "comparative"]},
            {"name": f"Характеристики {topic.lower()}", "intents": ["informational", "technical"]},
            {"name": f"Свойства {topic.lower()}", "intents": ["informational", "technical"]},
            {"name": f"Особенности {topic.lower()}", "intents": ["informational"]},
        ],
        
        # Процессы и методы
        "processes": [
            {"name": f"Установка {topic.lower()}", "intents": ["service", "diy", "informational"]},
            {"name": f"Монтаж {topic.lower()}", "intents": ["service", "commercial"]},
            {"name": f"Демонтаж {topic.lower()}", "intents": ["service"]},
            {"name": f"Настройка {topic.lower()}", "intents": ["service", "diy"]},
            {"name": f"Регулировка {topic.lower()}", "intents": ["service", "diy"]},
            {"name": f"Обслуживание {topic.lower()}", "intents": ["service"]},
            {"name": f"Уход за {topic.lower()}", "intents": ["informational", "diy"]},
            {"name": f"Эксплуатация {topic.lower()}", "intents": ["informational"]},
            {"name": f"Использование {topic.lower()}", "intents": ["informational"]},
            {"name": f"Применение {topic.lower()}", "intents": ["informational"]},
        ],
        
        # Бренды и производители
        "brands": [
            {"name": f"Производители {topic.lower()}", "intents": ["informational", "brand"]},
            {"name": f"Бренды {topic.lower()}", "intents": ["brand", "informational"]},
            {"name": f"Компании {topic.lower()}", "intents": ["brand", "commercial"]},
            {"name": f"Популярные марки {topic.lower()}", "intents": ["brand", "comparative"]},
            {"name": f"Лидеры рынка {topic.lower()}", "intents": ["brand", "informational"]},
            {"name": f"Рейтинг {topic.lower()}", "intents": ["comparative", "informational"]},
            {"name": f"Сравнение {topic.lower()}", "intents": ["comparative"]},
            {"name": f"Отзывы о {topic.lower()}", "intents": ["reviews", "comparative"]},
            {"name": f"Рекомендации {topic.lower()}", "intents": ["informational"]},
            {"name": f"Советы по {topic.lower()}", "intents": ["informational"]},
        ],
        
        # Локальные и срочные услуги
        "local_urgent": [
            {"name": f"{topic} рядом", "intents": ["local", "navigational"]},
            {"name": f"{topic} в городе", "intents": ["local", "commercial"]},
            {"name": f"Где найти {topic.lower()}", "intents": ["local", "navigational"]},
            {"name": f"Срочный {topic.lower()}", "intents": ["urgent", "commercial"]},
            {"name": f"{topic} быстро", "intents": ["urgent", "service"]},
            {"name": f"Экстренный {topic.lower()}", "intents": ["urgent", "service"]},
            {"name": f"{topic} 24/7", "intents": ["urgent", "service"]},
            {"name": f"Вызов для {topic.lower()}", "intents": ["urgent", "service"]},
            {"name": f"Адреса {topic.lower()}", "intents": ["local", "navigational"]},
            {"name": f"Контакты {topic.lower()}", "intents": ["navigational"]},
        ],
        
        # DIY и загрузки
        "diy_downloads": [
            {"name": f"Как сделать {topic.lower()}", "intents": ["diy", "informational"]},
            {"name": f"{topic} своими руками", "intents": ["diy"]},
            {"name": f"Инструкция {topic.lower()}", "intents": ["diy", "informational"]},
            {"name": f"Схема {topic.lower()}", "intents": ["diy", "download"]},
            {"name": f"Чертеж {topic.lower()}", "intents": ["download", "technical"]},
            {"name": f"Скачать {topic.lower()}", "intents": ["download"]},
            {"name": f"Документация {topic.lower()}", "intents": ["download", "informational"]},
            {"name": f"Руководство {topic.lower()}", "intents": ["download", "diy"]},
            {"name": f"Мануал {topic.lower()}", "intents": ["download", "informational"]},
            {"name": f"Самостоятельный {topic.lower()}", "intents": ["diy"]},
        ],
        
        # Отзывы и сравнения
        "reviews_comparison": [
            {"name": f"Отзывы {topic.lower()}", "intents": ["reviews"]},
            {"name": f"Мнения о {topic.lower()}", "intents": ["reviews", "informational"]},
            {"name": f"Опыт использования {topic.lower()}", "intents": ["reviews"]},
            {"name": f"Сравнить {topic.lower()}", "intents": ["comparative"]},
            {"name": f"Что лучше {topic.lower()}", "intents": ["comparative"]},
            {"name": f"Плюсы и минусы {topic.lower()}", "intents": ["comparative", "informational"]},
            {"name": f"Альтернативы {topic.lower()}", "intents": ["comparative"]},
            {"name": f"Аналоги {topic.lower()}", "intents": ["comparative"]},
            {"name": f"Выбор {topic.lower()}", "intents": ["comparative", "informational"]},
            {"name": f"Тест {topic.lower()}", "intents": ["comparative", "reviews"]},
        ],
        
        # Правовые и технические
        "legal_technical": [
            {"name": f"Лицензия на {topic.lower()}", "intents": ["legal"]},
            {"name": f"Разрешения {topic.lower()}", "intents": ["legal"]},
            {"name": f"Сертификация {topic.lower()}", "intents": ["legal", "informational"]},
            {"name": f"Нормативы {topic.lower()}", "intents": ["legal", "technical"]},
            {"name": f"ГОСТ {topic.lower()}", "intents": ["legal", "technical"]},
            {"name": f"Стандарты {topic.lower()}", "intents": ["technical", "legal"]},
            {"name": f"Спецификация {topic.lower()}", "intents": ["technical"]},
            {"name": f"Параметры {topic.lower()}", "intents": ["technical"]},
            {"name": f"Технические данные {topic.lower()}", "intents": ["technical"]},
            {"name": f"Требования к {topic.lower()}", "intents": ["technical", "legal"]},
        ]
    }
    
    # Собираем все шаблоны
    all_templates = []
    for category, templates in cluster_templates.items():
        all_templates.extend(templates)
    
    # Фильтруем по разрешенным интентам
    filtered_templates = []
    for template in all_templates:
        template_intents = [intent for intent in template["intents"] if intent in intents]
        if template_intents:
            filtered_templates.append({
                **template,
                "intents": template_intents
            })
    
    print(f"Filtered templates: {len(filtered_templates)}")
    print(f"Target clusters: {target_count}")
    
    # Расширяем список шаблонов для большого количества кластеров
    extended_templates = []
    
    # Добавляем базовые шаблоны
    extended_templates.extend(filtered_templates)
    
    # Создаем вариации с разными модификаторами
    variation_prefixes = [
        "Качественный", "Профессиональный", "Недорогой", "Быстрый", "Надежный",
        "Современный", "Элитный", "Бюджетный", "Премиум", "Стандартный",
        "Улучшенный", "Инновационный", "Проверенный", "Рекомендуемый", "Популярный"
    ]
    
    variation_suffixes = [
        "для дома", "для офиса", "для квартиры", "для коттеджа", "для дачи",
        "в Москве", "в регионах", "под ключ", "с гарантией", "со скидкой",
        "срочно", "качественно", "недорого", "быстро", "профессионально"
    ]
    
    # Генерируем вариации пока не достигнем нужного количества
    base_count = len(filtered_templates)
    while len(extended_templates) < target_count * 2:  # Создаем с запасом
        for base_template in filtered_templates:
            if len(extended_templates) >= target_count * 2:
                break
                
            # Добавляем префиксы
            for prefix in variation_prefixes:
                if len(extended_templates) >= target_count * 2:
                    break
                extended_templates.append({
                    "name": f"{prefix} {base_template['name'].lower()}",
                    "intents": base_template["intents"]
                })
            
            # Добавляем суффиксы
            for suffix in variation_suffixes:
                if len(extended_templates) >= target_count * 2:
                    break
                extended_templates.append({
                    "name": f"{base_template['name']} {suffix}",
                    "intents": base_template["intents"]
                })
    
    print(f"Extended templates: {len(extended_templates)}")
    
    # Генерируем кластеры до нужного количества
    for i in range(target_count):
        template = extended_templates[i % len(extended_templates)]
        
        # Создаем кластер
        cluster = {
            "cluster_id": str(i + 1),
            "name": template["name"],
            "intent_mix": template["intents"][:3],  # Максимум 3 интента
            "seed_examples": generate_seed_examples(template["name"], template["intents"][0] if template["intents"] else "informational"),
            "notes": f"Кластер по теме: {template['name']}"
        }
        
        clusters.append(cluster)
    
    return clusters

def generate_seed_examples(cluster_name: str, primary_intent: Intent) -> List[str]:
    """Генерирует примеры запросов для кластера."""
    examples = []
    
    # Базовые примеры на основе названия кластера
    base_name = cluster_name.lower()
    
    # Модификаторы по интентам
    if primary_intent == "commercial":
        modifiers = ["купить", "заказать", "цена", "стоимость", "недорого"]
    elif primary_intent == "service":
        modifiers = ["услуги", "ремонт", "установка", "монтаж", "обслуживание"]
    elif primary_intent == "informational":
        modifiers = ["что такое", "как", "виды", "типы", "характеристики"]
    elif primary_intent == "problem":
        modifiers = ["не работает", "сломался", "проблема", "неисправность", "ошибка"]
    elif primary_intent == "price":
        modifiers = ["цена", "стоимость", "расценки", "тариф", "сколько стоит"]
    elif primary_intent == "local":
        modifiers = ["рядом", "в городе", "адрес", "где найти", "контакты"]
    elif primary_intent == "urgent":
        modifiers = ["срочно", "быстро", "экстренно", "24/7", "вызов"]
    elif primary_intent == "reviews":
        modifiers = ["отзывы", "мнения", "опыт", "рекомендации", "советы"]
    elif primary_intent == "diy":
        modifiers = ["своими руками", "как сделать", "инструкция", "самостоятельно", "пошагово"]
    elif primary_intent == "download":
        modifiers = ["скачать", "загрузить", "документация", "схема", "руководство"]
    elif primary_intent == "technical":
        modifiers = ["характеристики", "параметры", "спецификация", "технические данные", "свойства"]
    elif primary_intent == "legal":
        modifiers = ["лицензия", "разрешение", "сертификат", "нормативы", "требования"]
    elif primary_intent == "comparative":
        modifiers = ["сравнить", "лучший", "рейтинг", "что выбрать", "плюсы минусы"]
    elif primary_intent == "brand":
        modifiers = ["производители", "бренды", "марки", "компании", "популярные"]
    elif primary_intent == "navigational":
        modifiers = ["официальный сайт", "контакты", "адрес", "телефон", "где найти"]
    else:
        modifiers = ["лучший", "качественный", "надежный", "проверенный", "рекомендуемый"]
    
    # Генерируем примеры
    for modifier in modifiers[:5]:
        if modifier in ["что такое", "как"]:
            examples.append(f"{modifier} {base_name}")
        else:
            examples.append(f"{modifier} {base_name}")
    
    return examples[:5]
