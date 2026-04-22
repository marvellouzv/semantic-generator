"""
GPT-5 генератор верхнеуровневых кластеров с reasoning.
Переделанная система генерации кластеров полностью на GPT-5.
"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json
import os
from pathlib import Path
from .query_normalizer import normalize_and_deduplicate_clusters
from .gpt5_wrapper import ask_gpt5

# Локальная фиксация модели, чтобы избежать циклического импорта.
# Для OpenRouter допускаем provider-prefixed model ids, например openai/gpt-5.1.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1"))
if "gpt-5" not in OPENAI_MODEL.lower():
    print(f"[WARN] Model '{OPENAI_MODEL}' does not look like GPT-5 family. Falling back to 'openai/gpt-5.1'")
    OPENAI_MODEL = "openai/gpt-5.1"

class QueryType(str, Enum):
    COMMERCIAL = "Коммерческие"
    INFORMATIONAL = "Информационные"
    SERVICE = "Сервисные"
    PRICE = "Ценовые"
    LOCAL = "Локальные"
    URGENT = "Срочные"
    REVIEWS = "Отзывы"
    COMPARATIVE = "Сравнительные"
    DIY = "Своими руками"
    DOWNLOADS = "Загрузки"
    TECHNICAL = "Технические"
    LEGAL = "Правовые"
    BRAND = "Брендовые"
    NAVIGATIONAL = "Навигационные"
    PROBLEM = "Проблемные"

# Маппинг наших Intent на QueryType
INTENT_TO_QUERY_TYPE = {
    "commercial": QueryType.COMMERCIAL,
    "informational": QueryType.INFORMATIONAL,
    "service": QueryType.SERVICE,
    "price": QueryType.PRICE,
    "local": QueryType.LOCAL,
    "urgent": QueryType.URGENT,
    "reviews": QueryType.REVIEWS,
    "comparative": QueryType.COMPARATIVE,
    "diy": QueryType.DIY,
    "download": QueryType.DOWNLOADS,
    "technical": QueryType.TECHNICAL,
    "legal": QueryType.LEGAL,
    "brand": QueryType.BRAND,
    "navigational": QueryType.NAVIGATIONAL,
    "problem": QueryType.PROBLEM
}

TYPE_RULES = {
    QueryType.COMMERCIAL: """
- Разрешить вершины с коммерческим намерением (поиск услуги/исполнителя/покупки).
- Допустимы НО НЕ ОБЯЗАТЕЛЬНЫ маркеры «услуги», «заказать», «купить»; избегать длинных хвостов.
- При конфликте с другими типами — держать формулировки короткими (1–3 слова).
""",
    QueryType.INFORMATIONAL: """
- Разрешить верхнеуровневые информ-запросы общего характера (что это, виды, назначение), но без хвостов и how-to.
- «Что такое»/«как работает» НЕ писать целиком — конденсировать в общий head («виды», «назначение», «принцип»).
""",
    QueryType.SERVICE: """
- Акцент на обслуживании и работах: «ремонт», «установка», «обслуживание», «регулировка», «замена».
- Каждая из перечисленных — самостоятельная вершина, если релевантна теме.
""",
    QueryType.PRICE: """
- Разрешить отдельные head-кластеры «цены», «стоимость», «расценки», «прайс-лист», «сколько стоит».
- Без сумм/валют/городов и без уточняющих хвостов.
""",
    QueryType.LOCAL: """
- Разрешить навигацию по близости: «рядом», «адрес», «где», «поблизости», «на карте».
- ЗАПРЕЩЕНЫ геомодификаторы с названиями городов: «в Москве», «в СПб», «в Новосибирске» и т.д.
- Только общие локальные запросы БЕЗ указания конкретных городов.
""",
    QueryType.URGENT: """
- Разрешить «срочный», «экстренный», «24/7», «круглосуточно» как вершины, если применимо к теме.
- Формулировки держать краткими: «срочный ремонт», «ремонт 24/7» и т.п., без телефонов/каналов.
""",
    QueryType.REVIEWS: """
- Разрешить кластеры «отзывы», «рейтинг», «мнения», «оценки».
- Не добавлять бренды/гео; держать общие head-формы.
""",
    QueryType.COMPARATIVE: """
- Разрешить вершины выбора: «лучший», «рейтинг», «сравнение», «топ».
- Держать их как общие heads без уточнений (не добавлять «для ...», «между ...»).
""",
    QueryType.DIY: """
- Разрешить общий DIY-верх: «инструкция», «схема», «самостоятельно».
- Избегать how-to хвостов («как сделать X»); только обобщающие вершины.
""",
    QueryType.DOWNLOADS: """
- Разрешить «скачать», «шаблон», «образец», «схема» как отдельные heads (без форматов и брендов).
""",
    QueryType.TECHNICAL: """
- Разрешить «параметры», «характеристики», «свойства», «технические данные», «комплектация» (общие heads).
""",
    QueryType.LEGAL: """
- Разрешить «лицензия», «сертификат», «ГОСТ», «требования», «нормы».
- Без юридических хвостов («по закону ...»); только head-формы.
""",
    QueryType.BRAND: """
- Разрешить бренды ТОЛЬКО из whitelist. Если whitelist пуст — брендовые кластеры не генерировать.
- Бренды давать как отдельные вершины без моделей/серий.
""",
    QueryType.NAVIGATIONAL: """
- Разрешить «официальный сайт», «контакты», «телефон», «адрес» как навигационные head-кластеры.
- Без доменов, телефонов и брендов.
""",
    QueryType.PROBLEM: """
- Разрешить кластеры неисправностей/симптомов: «не работает», «сломался», «течет», «шумит», «проблема».
- Без добавления «что делать»/«почему» — только head-формы.
"""
}

def get_system_prompt(locale: str = "ru-RU") -> str:
    """Базовый системный промпт для GPT-5."""
    return f"""
Ты — старший SEO-стратег и эксперт по кластеризации для российского рынка (Google RU + Яндекс).
Специализация: извлечение «верхнеуровневых» head-запросов (ВЧ/СЧ ядро, без длинных хвостов) для дальнейшей декомпозиции.
Рабочая локаль: {locale}.
Всегда соблюдай формат OUTPUT (STRICT) и правила нормализации ниже.
""".strip()

def build_type_directives(selected_types: List[Union[QueryType, str]], brand_whitelist: Optional[List[str]] = None) -> str:
    """Строит динамические правила для выбранных типов запросов.

    Принимает как значения перечисления QueryType, так и строковые интенты
    из UI (например, 'commercial', 'informational')."""

    # Нормализуем вход в список QueryType
    normalized_selected: List[QueryType] = []
    for item in selected_types:
        if isinstance(item, QueryType):
            normalized_selected.append(item)
        elif isinstance(item, str):
            mapped = INTENT_TO_QUERY_TYPE.get(item)
            if mapped:
                normalized_selected.append(mapped)
            else:
                # Попытка сопоставить по имени Enum (на всякий случай)
                try:
                    normalized_selected.append(QueryType[item.upper()])
                except Exception:
                    continue

    all_types = list(QueryType)
    disallowed = [t for t in all_types if t not in normalized_selected]
    
    # Блок разрешенных правил
    allow_block = "\n".join([
        f"### {query_type.value}\n{TYPE_RULES[query_type].strip()}"
        for query_type in normalized_selected
    ])
    
    # Правило для брендов
    if QueryType.BRAND in selected_types:
        brands = ", ".join(brand_whitelist) if brand_whitelist else "— (пусто, бренды не выводить)"
        brand_rule = f"- Брендовые кластеры разрешены ТОЛЬКО из whitelist: {brands}.\n"
    else:
        brand_rule = "- Все брендовые запросы запрещены.\n"
    
    selected_names = [t.value for t in normalized_selected]
    disallowed_names = [t.value for t in disallowed]
    
    return f"""
РАЗРЕШЕНЫ ТОЛЬКО следующие типы запросов (остальные исключить):
{", ".join(selected_names) or "— (ничего не выбрано)"}.

{brand_rule}
Дополнительные правила по разрешённым типам:
{allow_block}

Запрещённые типы (НЕ генерировать): {", ".join(disallowed_names) or "—"}.
""".strip()

def get_fixed_rules() -> str:
    """Фиксированные правила генерации."""
    # Load from prompts file so it can be edited without code changes.
    repo_root = Path(__file__).resolve().parents[2]
    prompt_path = repo_root / "prompts" / "gpt5_head_queries_fixed_rules.md"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"[WARN] Failed to load fixed rules prompt from {prompt_path}: {e}")
        # Minimal fallback (keeps system running if file missing)
        return "OUTPUT (STRICT)\n- Return one markdown table with columns: Head Query | Intent | Group | Demand Level | Parent Theme"

def parse_multiple_topics(topic: str) -> str:
    """
    Обрабатывает множественные темы через запятую и создает комплексный промпт.
    """
    if ',' in topic:
        topics = [t.strip() for t in topic.split(',') if t.strip()]
        if len(topics) > 1:
            return f"комплексная тематика: {topic} (включая все связанные направления: {', '.join(topics)})"
    return topic

def _build_region_variants(regions: Optional[List[str]]) -> Dict[str, List[str]]:
    """Маппинг регион -> список допустимых вариантов (RU)."""
    if not regions:
        return {}

    canonical = [r.strip() for r in regions if r and r.strip()]
    out: Dict[str, List[str]] = {}

    # Кураторский набор синонимов/сокращений для популярных регионов.
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
        variants = curated.get(key)
        if not variants:
            # Fallback: ровно как ввели + "в {регион}"
            variants = [r, f"в {r}"]

        # de-dup preserve order
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


def build_gpt5_prompt(
    topic: str,
    selected_intents: List[str],
    brand_whitelist: Optional[List[str]] = None,
    locale: str = "ru-RU",
    minus_words: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Строит промпт для GPT-5 на основе выбранных интентов.
    
    Args:
        topic: Тематика
        selected_intents: Список выбранных интентов (наш формат)
        brand_whitelist: Список разрешенных брендов
        locale: Локаль
    
    Returns:
        Dict с 'system' и 'user' промптами
    """
    
    # Конвертируем наши интенты в русские названия
    intent_to_russian = {
        "commercial": "Коммерческие",
        "informational": "Информационные", 
        "service": "Сервисные",
        "price": "Ценовые",
        "local": "Локальные",
        "urgent": "Срочные",
        "reviews": "Отзывы",
        "comparative": "Сравнительные",
        "diy": "Своими руками",
        "download": "Загрузки",
        "technical": "Технические",
        "legal": "Правовые",
        "brand": "Брендовые",
        "navigational": "Навигационные",
        "problem": "Проблемные"
    }
    
    allowed_types = [intent_to_russian.get(intent, intent) for intent in selected_intents]
    allowed_types_str = ", ".join(allowed_types)
    
    # Определяем whitelist для брендов
    brand_whitelist_str = ", ".join(brand_whitelist) if brand_whitelist else "--"
    
    # Формируем coverage checklist ТОЛЬКО на основе выбранных типов
    coverage_items = []
    
    # Добавляем пункты только для выбранных типов
    if "commercial" in selected_intents:
        coverage_items.append(f"- Commercial queries: buying, ordering services related to \"{topic}\"")
    
    if "informational" in selected_intents:
        coverage_items.append(f"- Informational queries: what is, how it works, types of \"{topic}\"")
    
    if "service" in selected_intents:
        coverage_items.append(f"- Service queries: repair, installation, maintenance of \"{topic}\"")
    
    if "price" in selected_intents:
        coverage_items.append(f"- Price queries: cost, pricing, rates for \"{topic}\"")
    
    region_map = _build_region_variants(regions)
    if "local" in selected_intents:
        if region_map:
            coverage_items.append(f"- Local queries: ONLY for the selected regions (with variants), no other geos")
        else:
            coverage_items.append(f"- Local queries: nearby, addresses for \"{topic}\" (NO city names like 'в Москве', 'в СПб')")
    
    if "urgent" in selected_intents:
        coverage_items.append(f"- Urgent queries: fast, emergency, 24/7 for \"{topic}\"")
    
    if "reviews" in selected_intents:
        coverage_items.append(f"- Review queries: reviews, opinions, experiences with \"{topic}\"")
    
    if "comparative" in selected_intents:
        coverage_items.append(f"- Comparison queries: best, compare, rating of \"{topic}\"")
    
    if "diy" in selected_intents:
        coverage_items.append(f"- DIY queries: how to do, instructions for \"{topic}\"")
    
    if "download" in selected_intents:
        coverage_items.append(f"- Download queries: download, documentation, files for \"{topic}\"")
    
    if "technical" in selected_intents:
        coverage_items.append(f"- Technical queries: specifications, parameters of \"{topic}\"")
    
    if "legal" in selected_intents:
        coverage_items.append(f"- Legal queries: licenses, certificates, requirements for \"{topic}\"")
    
    if "brand" in selected_intents:
        coverage_items.append(f"- Brand queries: brands, manufacturers of \"{topic}\" (use whitelist only)")
    
    if "navigational" in selected_intents:
        coverage_items.append(f"- Navigational queries: official sites, contacts for \"{topic}\"")
    
    if "problem" in selected_intents:
        coverage_items.append(f"- Problem queries: troubleshooting, errors, issues with \"{topic}\"")
    
    coverage_checklist = "\n".join(coverage_items) if coverage_items else f"- All aspects of \"{topic}\""
    
    # Простой системный промпт (пустой) + доп. правила будут в user_prompt
    system_prompt = ""

    minus_words_clean = [w.strip() for w in (minus_words or []) if w and w.strip()]
    minus_block = ""
    if minus_words_clean:
        minus_block = "NEGATIVE WORDS (STRICT):\n" + "\n".join([f"- {w}" for w in minus_words_clean]) + "\n"

    region_block = ""
    if "local" in selected_intents and region_map:
        region_lines = []
        for reg, vars_ in region_map.items():
            region_lines.append(f"- {reg}: {', '.join(vars_)}")
        region_block = (
            "REGION RULES FOR LOCAL QUERIES (STRICT):\n"
            "Local queries MUST be ONLY for these regions and MUST include exactly ONE of the allowed region variants below.\n"
            "Do NOT use any other cities/regions.\n"
            + "\n".join(region_lines)
            + "\n"
        )
    
    # Оптимизированный промпт: универсальный, фокус на тематику, естественность
    user_prompt = f"""You are a senior SEO strategist specializing in the Russian market (Yandex + Google RU).

TASK: Generate a comprehensive list of high-frequency search queries for the topic: "{parse_multiple_topics(topic)}"

CONTEXT:
- Target market: Russia/CIS, Russian language
- Query types to include: {allowed_types_str}
{"- Allowed brands: " + brand_whitelist_str if brand_whitelist else "- No brand queries"}

{minus_block}{region_block}
CRITICAL RULES (STRICT ENFORCEMENT):
1. Every query MUST be directly related to "{parse_multiple_topics(topic)}" - include topic-specific words in each query
2. Generate natural search queries EXACTLY as real users would type them in search engines
   - NO parentheses: "курсы по ИИ (XAI)" -> "курсы по объяснимому ИИ" or just "курсы по ИИ"
   - NO slashes: "CI/CD для ИИ" -> "CI CD для ИИ" or "непрерывная интеграция для ИИ"
   - NO special symbols: only letters, numbers, spaces

3. Queries should be 2-7 words (prefer shorter, but don't sacrifice naturalness)
4. Cover ALL major aspects of the topic comprehensively
5. **MANDATORY**: ONLY generate query types that are listed in "Query types to include": {allowed_types_str}
   - If "Локальные" is NOT in the list -> DO NOT generate location/geo queries
   - If "Локальные" is in the list AND регионы НЕ указаны -> generate ONLY general local queries WITHOUT city names (NO "в Москве", "в СПб", etc.)
   - If "Локальные" is in the list AND регионы указаны -> generate ONLY for selected regions (see REGION RULES) incl. variations (e.g. "в СПб", "Питер")
   - If "Навигационные" is NOT in the list -> DO NOT generate navigational queries  
   - If "Брендовые" is NOT in the list -> DO NOT generate brand queries
   - If "Ценовые" is NOT in the list -> DO NOT generate pricing queries
   - Strictly adhere to the allowed types only!

WHAT TO AVOID (CRITICAL):
- Generic single-word queries without topic context ("цены", "стоимость", "купить")
- Long-tail queries with too many details (keep it to max 7 words)
- Duplicate queries with same meaning
- **ANY query types NOT explicitly listed in "Query types to include" above**
- Do NOT infer or add query types that were not selected
- Parentheses, slashes, special symbols like / ( ) [ ]
- **CITY NAMES in local queries**: if регионы НЕ указаны -> NO "в Москве", "в СПб", etc. If регионы указаны -> ONLY allowed variants from REGION RULES.

EXAMPLES OF GOOD vs BAD (universal pattern):
GOOD: Natural queries with topic context:
  - "ремонт холодильников"
  - "цена установки окон"
  - "купить матрас онлайн"
  - "курсы машинного обучения"
  - "обучение нейросетям онлайн"
  - "seo продвижение рядом" (local query WITHOUT city name)

BAD: Unnatural or generic queries:
  - "ремонт", "цена", "купить" (no topic context)
  - "курсы по ИИ (XAI)" (has parentheses)
  - "CI/CD для ИИ" (has slash)
  - "машинное обучение и/или ИИ" (has special symbols)
  - "seo продвижение в москве" (local query WITH city name - FORBIDDEN)
  - "seo продвижение в спб" (local query WITH city name - FORBIDDEN)

OUTPUT FORMAT:
Markdown table with exactly these columns:
- Head Query (the actual search query in Russian, must contain topic-specific words)
- Intent (commercial / informational / unknown) — general intent only (NOT the UI query type)
- Group (one of the allowed query types in Russian from UI, e.g. "Отзывы"; MUST be from the allowed list)
- Demand Level (High / Medium / Low)
    - Parent Theme (category name in Russian). IMPORTANT: this is NOT the same as Parent Category.

Generate MAXIMUM possible queries organized into comprehensive Parent Themes that cover ALL aspects of "{parse_multiple_topics(topic)}". No limits on quantity - aim for complete, exhaustive coverage.

COVERAGE CHECKLIST:
{coverage_checklist}

Start generating the table now:"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }

def parse_gpt5_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Парсит ответ GPT-5 и конвертирует в формат кластеров.
    
    Args:
        response_text: Текст ответа от GPT-5
        
    Returns:
        Список кластеров в нашем формате
    """
    
    clusters = []
    
    # Проверяем, что response_text является строкой и не пустой
    if not response_text or not isinstance(response_text, str):
        print(f"[WARN] Invalid response_text: {type(response_text)} = {response_text}")
        return clusters
    
    # Проверяем, что строка не пустая после strip
    response_text = response_text.strip()
    if not response_text:
        print("[WARN] Empty response_text after strip")
        return clusters
    
    lines = response_text.split('\n')
    print(f"[DEBUG] Parsing response: {len(lines)} lines")
    print(f"[DEBUG] First few lines: {lines[:5]}")
    
    # Ищем таблицу
    table_started = False
    cluster_id = 1
    
    # Маппинги для нормализации
    intent_to_russian = {
        "commercial": "Коммерческие",
        "informational": "Информационные",
        "service": "Сервисные",
        "price": "Ценовые",
        "local": "Локальные",
        "urgent": "Срочные",
        "reviews": "Отзывы",
        "comparative": "Сравнительные",
        "diy": "Своими руками",
        "download": "Загрузки",
        "technical": "Технические",
        "legal": "Правовые",
        "brand": "Брендовые",
        "navigational": "Навигационные",
        "problem": "Проблемные",
    }
    russian_to_intent = {v.lower(): k for k, v in intent_to_russian.items()}

    def normalize_intent_code(raw: str) -> str:
        if not raw:
            return "informational"
        lower = raw.strip().lower()

        # Russian label -> code
        if lower in russian_to_intent:
            return russian_to_intent[lower]

        # Common legacy/alias intents from older prompts
        legacy_map = {
            "transactional": "commercial",
            "transact": "commercial",
            "коммерческие": "commercial",
            "информационные": "informational",
            "навигационные": "navigational",
        }
        if lower in legacy_map:
            return legacy_map[lower]

        # Direct code
        if lower in intent_to_russian:
            return lower

        return "informational"

    def normalize_parent_category(raw: str, fallback_intent: str) -> str:
        if raw and raw.strip():
            # If already Russian category label
            if raw.strip().lower() in russian_to_intent:
                return intent_to_russian[russian_to_intent[raw.strip().lower()]]
            # If it is an intent code
            intent_code = normalize_intent_code(raw)
            return intent_to_russian.get(intent_code, raw.strip())
        return intent_to_russian.get(fallback_intent, "Информационные")

    for i, line in enumerate(lines):
        line = line.strip()
        
        # Пропускаем заголовки таблицы
        if '|' in line and ('Head Query' in line or '---' in line):
            table_started = True
            print(f"[DEBUG] Table header found at line {i+1}: {line}")
            continue
            
        # Парсим строки таблицы
        if table_started and '|' in line and line.count('|') >= 3:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            print(f"[DEBUG] Parsing table row {i+1}: {line} -> {parts}")
            
            if len(parts) >= 4:
                head_query = parts[0]

                # Expected format (5 columns):
                # | Head Query | Intent | Group | Demand Level | Parent Theme |
                #
                # Backward compatible (4 columns):
                # | Head Query | Group (or legacy intent) | Demand Level | Parent Theme |

                def normalize_simple_intent(raw: str) -> str:
                    if not raw:
                        return "unknown"
                    low = raw.strip().lower()
                    if low in ("commercial", "коммерческий", "коммерч", "коммерческий intent"):
                        return "commercial"
                    if low in ("informational", "информационный", "инфо", "информационный intent"):
                        return "informational"
                    if low in ("unknown", "не определено", "неопределено", "n/a", "na"):
                        return "unknown"
                    # tolerate legacy
                    if low in ("transactional", "service", "price", "local", "navigational"):
                        return "commercial"
                    return "unknown"

                def group_label_to_code(label: str) -> str:
                    if not label:
                        return "informational"
                    low = label.strip().lower()
                    if low in russian_to_intent:
                        return russian_to_intent[low]
                    # If already code
                    if low in intent_to_russian:
                        return low
                    return "informational"

                if len(parts) >= 5:
                    simple_intent = normalize_simple_intent(parts[1])
                    group_label = normalize_parent_category(parts[2], group_label_to_code(parts[2]))
                    demand_level = parts[3]
                    parent_theme = parts[4]
                else:
                    # 4-column legacy
                    group_like = parts[1]
                    demand_level = parts[2]
                    parent_theme = parts[3]
                    group_code = group_label_to_code(group_like)
                    group_label = normalize_parent_category(group_like, group_code)
                    # derive simple intent from group if possible, else unknown
                    if group_code in ("informational", "technical", "legal", "comparative", "diy", "download", "reviews", "problem", "brand", "navigational"):
                        simple_intent = "informational"
                    elif group_code in ("commercial", "service", "price", "local", "urgent"):
                        simple_intent = "commercial"
                    else:
                        simple_intent = "unknown"

                group_code = group_label_to_code(group_label)

                cluster = {
                    "cluster_id": str(cluster_id),
                    "name": head_query,
                    "parent_category": group_label,     # Group label (RU)
                    "intent_mix": [group_code],         # Group code (matches UI types)
                    "seed_examples": [head_query],
                    "notes": f"Intent: {simple_intent}, Group: {group_label}, Parent Theme: {parent_theme}, Demand: {demand_level}",
                    "demand_level": demand_level,
                    "parent_theme": parent_theme,
                    "gpt_intent": simple_intent,        # Simple intent (commercial/informational/unknown)
                }
                
                clusters.append(cluster)
                cluster_id += 1
    
    return clusters

async def generate_clusters_gpt5_single(
    topic: str,
    selected_intents: List[str],
    target_count: int,
    brand_whitelist: Optional[List[str]] = None,
    minus_words: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Генерирует кластеры через GPT-5 с reasoning.
    
    Args:
        topic: Тематика
        selected_intents: Выбранные интенты
        target_count: Целевое количество кластеров
        openai_client: Клиент OpenAI
        brand_whitelist: Список брендов для брендовых запросов
        
    Returns:
        Список сгенерированных кластеров
    """
    
    try:
        # Строим промпт
        prompts = build_gpt5_prompt(
            topic,
            selected_intents,
            brand_whitelist,
            minus_words=minus_words,
            regions=regions,
        )
        
        print(f"[GPT5] Sending prompt to GPT-5 ({len(prompts['user'])} chars)")
        print("----- PROMPT START -----")
        print(prompts["user"])  # Полный промпт для проверки
        print("------ PROMPT END ------")
        
        # Используем новый ask_gpt5() wrapper с нормализацией и обработкой ошибок
        print(f"[GPT5] Model: {OPENAI_MODEL}")
        
        response_text = await ask_gpt5(
            input_blocks=[
                {"role": "user", "content": [{"type": "input_text", "text": prompts["user"]}]}
            ],
            model=OPENAI_MODEL,
            max_output_tokens=16000,
        )
        print("[GPT-5] Response received")
        print(f"[GPT-5] Response length: {len(response_text)} chars")
        print(f"[GPT-5] Response preview: {response_text[:200]}...")
        
        # Парсим ответ
        clusters = parse_gpt5_response(response_text)
        
        # Применяем нормализацию и дедупликацию
        normalized_clusters = normalize_and_deduplicate_clusters(clusters)
        
        # Обрезаем только если есть явное ограничение (target_count > 0)
        if target_count > 0 and len(normalized_clusters) > target_count:
            normalized_clusters = normalized_clusters[:target_count]
        
        print(f"[SUCCESS] Generated {len(normalized_clusters)} clusters")
        return normalized_clusters
        
    except Exception as e:
        print(f"Error in GPT-5 generation: {e}")
        
        # Детальное логирование ошибок OpenAI
        if hasattr(e, 'response'):
            print(f"OpenAI API Error Details:")
            print(f"Status Code: {getattr(e.response, 'status_code', 'Unknown')}")
            print(f"Response Text: {getattr(e.response, 'text', 'No response text')}")
        
        if hasattr(e, 'body'):
            print(f"Error Body: {e.body}")
            
        import traceback
        traceback.print_exc()
        
        print(f"[ERROR] RETURN from generate_clusters_gpt5_single: [] (ERROR)")
        return []

async def generate_clusters_gpt5_expansion(
    topic: str,
    selected_intents: List[str],
    existing_clusters: List[Dict[str, Any]],
    target_additional: int,
    brand_whitelist: Optional[List[str]] = None,
    minus_words: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Генерирует дополнительные кластеры на основе уже существующих."""
    
    existing_names = [cluster.get("name", "") for cluster in existing_clusters]
    existing_themes = list(set([cluster.get("parent_theme", "") for cluster in existing_clusters if cluster.get("parent_theme")]))
    
    # Конвертируем наши интенты в русские названия
    intent_to_russian = {
        "commercial": "Коммерческие",
        "informational": "Информационные", 
        "service": "Сервисные",
        "price": "Ценовые",
        "local": "Локальные",
        "urgent": "Срочные",
        "reviews": "Отзывы",
        "comparative": "Сравнительные",
        "diy": "Своими руками",
        "download": "Загрузки",
        "technical": "Технические",
        "legal": "Правовые",
        "brand": "Брендовые",
        "navigational": "Навигационные",
        "problem": "Проблемные"
    }
    
    allowed_types = [intent_to_russian.get(intent, intent) for intent in selected_intents]
    allowed_types_str = ", ".join(allowed_types)

    minus_words_clean = [w.strip() for w in (minus_words or []) if w and w.strip()]
    minus_block = ""
    if minus_words_clean:
        minus_block = "NEGATIVE WORDS (STRICT):\n" + "\n".join([f"- {w}" for w in minus_words_clean]) + "\n"

    region_map = _build_region_variants(regions)
    region_block = ""
    if "local" in selected_intents and region_map:
        region_lines = []
        for reg, vars_ in region_map.items():
            region_lines.append(f"- {reg}: {', '.join(vars_)}")
        region_block = (
            "REGION RULES FOR LOCAL QUERIES (STRICT):\n"
            "Local queries MUST be ONLY for these regions and MUST include exactly ONE of the allowed region variants below.\n"
            "Do NOT use any other cities/regions.\n"
            + "\n".join(region_lines)
            + "\n"
        )
    
    expansion_prompt = f"""You have {len(existing_clusters)} existing clusters for topic "{topic}".

EXISTING CLUSTERS:
{chr(10).join([f"- {name}" for name in existing_names[:20]])}

EXISTING PARENT THEMES:
{", ".join(existing_themes)}

{minus_block}{region_block}
TASK: Generate additional clusters that:
1) DO NOT duplicate existing clusters
2) Cover missing aspects of "{topic}"
3) **STRICT**: ONLY use these query types: {allowed_types_str}
   - Do NOT generate any query types NOT in this list
   - If "Локальные" is NOT listed -> NO location/geo queries
   - If "Локальные" is listed AND регионы НЕ указаны -> general local queries WITHOUT city names (NO "в Москве", "в СПб", etc.)
   - If "Локальные" is listed AND регионы указаны -> ONLY selected regions (see REGION RULES) incl. variations
   - If "Навигационные" is NOT listed -> NO navigational queries
   - If "Брендовые" is NOT listed -> NO brand queries
4) Create new Parent Themes or complement existing ones
5) Each query must contain topic-specific words (not generic terms)
6) **CRITICAL**: Generate ONLY natural queries as real users type them
   - NO parentheses, slashes, or special symbols
   - Only letters, numbers, spaces
   - Example: "курсы по ИИ (XAI)" -> "курсы по объяснимому ИИ"

Return ONLY the markdown table:

| Head Query | Intent | Group | Demand Level | Parent Theme |
|------------|--------|-------|--------------|--------------|

Сфокусируйся на пропущенных аспектах и новых углах зрения на тематику."""

    try:
        response_text = await ask_gpt5(
            input_blocks=[
                {"role": "user", "content": [{"type": "input_text", "text": expansion_prompt}]}
            ],
            model=OPENAI_MODEL,
            max_output_tokens=12000,
        )
        print(f"Expansion response length: {len(response_text)}")
        
        # Парсим дополнительные кластеры
        additional_clusters = parse_gpt5_response(response_text)
        
        # Присваиваем новые ID
        start_id = len(existing_clusters) + 1
        for i, cluster in enumerate(additional_clusters):
            cluster["cluster_id"] = str(start_id + i)
        
        return additional_clusters
        
    except Exception as e:
        print(f"Error in expansion: {e}")
        
        # Детальное логирование ошибок OpenAI
        if hasattr(e, 'response'):
            print(f"OpenAI API Error Details (expansion):")
            print(f"Status Code: {getattr(e.response, 'status_code', 'Unknown')}")
            print(f"Response Text: {getattr(e.response, 'text', 'No response text')}")
        
        if hasattr(e, 'body'):
            print(f"Error Body: {e.body}")
            
        import traceback
        traceback.print_exc()
        
        return []

async def generate_clusters_gpt5(
    topic: str,
    selected_intents: List[str],
    target_count: int,
    brand_whitelist: Optional[List[str]] = None,
    minus_words: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
    use_ensemble: bool = True,
    use_parallel: bool = True,
) -> List[Dict[str, Any]]:
    """
    Генерирует кластеры через GPT-5 с улучшенной логикой ансамбля.
    
    Args:
        topic: Тематика
        selected_intents: Выбранные интенты
        target_count: Целевое количество кластеров
        openai_client: Клиент OpenAI
        brand_whitelist: Список брендов для брендовых запросов
        use_ensemble: Использовать ли ансамбль из нескольких вызовов
        use_parallel: Использовать ли параллельные запросы для разных интентов (FAST!)
        
    Returns:
        Список сгенерированных кластеров
    """
    print(f"[GPT5] Generating clusters for topic: '{topic}'")
    
    # Если выбран параллельный режим и несколько интентов, используем параллельную генерацию
    if use_parallel and len(selected_intents) > 1:
        print(f"[GPT5] Using PARALLEL mode for {len(selected_intents)} intents (FAST!)")
        return await generate_clusters_gpt5_parallel(
            topic=topic,
            selected_intents=selected_intents,
            target_count=target_count,
            brand_whitelist=brand_whitelist,
            minus_words=minus_words,
            regions=regions,
        )
    
    if not use_ensemble:
        # Простой одиночный вызов
        return await generate_clusters_gpt5_single(
            topic=topic,
            selected_intents=selected_intents,
            target_count=target_count,
            brand_whitelist=brand_whitelist,
            minus_words=minus_words,
            regions=regions,
        )
    
    # Определяем стратегию в зависимости от target_count
    if target_count == 0:
        # Максимальное покрытие без ограничений
        base_target = 0  # Без ограничений для максимального покрытия
        expansion_target = 0  # Без ограничений для максимального покрытия
    else:
        # Ограниченное количество
        base_target = target_count // 2
        expansion_target = target_count - base_target
    
    # Шаг 1: Получаем базовый ответ
    base_clusters = await generate_clusters_gpt5_single(
        topic=topic,
        selected_intents=selected_intents,
        target_count=base_target,
        brand_whitelist=brand_whitelist,
        minus_words=minus_words,
        regions=regions,
    )
    
    if not base_clusters:
        print("[ENSEMBLE] Base call failed")
        return []
    
    print(f"Step 1 complete: {len(base_clusters)} base clusters")
    
    # Шаг 2: Всегда запрашиваем дополнение для максимального покрытия
    print(f"[ENSEMBLE] Step 2: Requesting {expansion_target} additional clusters for maximum coverage")
    
    additional_clusters = await generate_clusters_gpt5_expansion(
        topic=topic,
        selected_intents=selected_intents,
        existing_clusters=base_clusters,
        target_additional=expansion_target,
        brand_whitelist=brand_whitelist,
        minus_words=minus_words,
        regions=regions,
    )
    
    print(f"[ENSEMBLE] Step 2 complete: {len(additional_clusters)} additional clusters")
    
    # Объединяем результаты
    all_clusters = base_clusters + additional_clusters
    
    # Финальная дедупликация
    final_clusters = normalize_and_deduplicate_clusters(all_clusters)
    
    # БЕЗ ОБРЕЗКИ - возвращаем все сгенерированные кластеры
    if target_count == 0:
        # Режим максимального покрытия - возвращаем все
        print("Returning ALL clusters (no limits)")
    else:
        # Ограниченный режим - обрезаем
        final_clusters = final_clusters[:target_count]
    
    print(f"Final improved ensemble result: {len(final_clusters)} clusters")
    return final_clusters

async def generate_clusters_gpt5_parallel(
    topic: str,
    selected_intents: List[str],
    target_count: int,
    brand_whitelist: Optional[List[str]] = None,
    minus_words: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Генерирует кластеры через параллельные запросы к GPT-5 для каждого интента отдельно.
    Это значительно ускоряет генерацию для множественных интентов.
    
    Args:
        topic: Тематика
        selected_intents: Выбранные интенты
        target_count: Целевое количество кластеров (распределяется между интентами)
        brand_whitelist: Список брендов для брендовых запросов
        
    Returns:
        Список сгенерированных кластеров
    """
    import asyncio
    
    print(f"[GPT5_PARALLEL] Starting parallel generation for {len(selected_intents)} intents")
    
    # Если только один интент, нет смысла в параллелизме
    if len(selected_intents) <= 1:
        return await generate_clusters_gpt5_single(
            topic,
            selected_intents,
            target_count,
            brand_whitelist,
            minus_words=minus_words,
            regions=regions,
        )
    
    # Распределяем target_count между интентами
    if target_count > 0:
        count_per_intent = max(10, target_count // len(selected_intents))
    else:
        count_per_intent = 0  # 0 = без ограничений
    
    # Создаем задачи для параллельного выполнения
    tasks = []
    for intent in selected_intents:
        task = generate_clusters_gpt5_single(
            topic=topic,
            selected_intents=[intent],  # Только один интент за раз
            target_count=count_per_intent,
            brand_whitelist=brand_whitelist,
            minus_words=minus_words,
            regions=regions,
        )
        tasks.append(task)
    
    # Запускаем все задачи параллельно
    print(f"[GPT5_PARALLEL] Launching {len(tasks)} parallel requests ({count_per_intent} clusters each)")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Собираем все успешные результаты
    all_clusters = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[GPT5_PARALLEL] Intent {selected_intents[i]} failed: {result}")
            continue
        if result:
            print(f"[GPT5_PARALLEL] Intent {selected_intents[i]}: {len(result)} clusters")
            all_clusters.extend(result)
    
    # Финальная дедупликация
    final_clusters = normalize_and_deduplicate_clusters(all_clusters)
    
    # Обрезка до target_count если нужно
    if target_count > 0 and len(final_clusters) > target_count:
        final_clusters = final_clusters[:target_count]
    
    print(f"[GPT5_PARALLEL] Total: {len(final_clusters)} clusters from {len(selected_intents)} parallel requests")
    return final_clusters

async def expand_template_with_gpt5(
    template,
    selected_intents: List[str],
    brand_whitelist: Optional[List[str]] = None,
    new_topic: Optional[str] = None,
    minus_words: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Расширяет существующий шаблон новыми кластерами через GPT-5.
    """
    print(f"Expanding template '{template.name}' with {len(template.clusters)} existing clusters")
    
    # Подготавливаем список существующих кластеров для контекста
    existing_clusters_text = "\n".join([
        f"- {cluster.name} ({cluster.parent_theme or 'Без темы'})"
        for cluster in template.clusters
    ])
    
    # Создаем промпт для расширения
    type_directives = build_type_directives(selected_intents, brand_whitelist)
    fixed_rules = get_fixed_rules()
    topic_for_prompt = parse_multiple_topics(new_topic if (new_topic and new_topic.strip()) else template.topic)

    minus_words_clean = [w.strip() for w in (minus_words or []) if w and w.strip()]
    minus_block = ""
    if minus_words_clean:
        minus_block = "NEGATIVE WORDS (STRICT):\n" + "\n".join([f"- {w}" for w in minus_words_clean]) + "\n"

    region_map = _build_region_variants(regions)
    region_block = ""
    if "local" in selected_intents and region_map:
        region_lines = []
        for reg, vars_ in region_map.items():
            region_lines.append(f"- {reg}: {', '.join(vars_)}")
        region_block = (
            "REGION RULES FOR LOCAL QUERIES (STRICT):\n"
            "Local queries MUST be ONLY for these regions and MUST include exactly ONE of the allowed region variants below.\n"
            "Do NOT use any other cities/regions.\n"
            + "\n".join(region_lines)
            + "\n"
        )
    
    expansion_prompt = f"""Act like a senior SEO strategist and keyword clustering expert for the Russian market (Google RU + Яндекс).
You specialize in extracting "верхнеуровневые" head queries (ВЧ/СЧ «ядро», без длинных хвостов).

OBJECTIVE
Дополнить существующий набор кластеров НОВЫМИ head-запросами, которые покроют пропущенные аспекты тематики. Если указана новая тематика, учесть её и расширить покрытие, не удаляя существующие вершины.

INPUT
- Текущая тематика шаблона: "{template.topic}"
- Новая тематика для дополнения: "{topic_for_prompt}"
- Существующие кластеры ({len(template.clusters)} шт.):
{existing_clusters_text}

ЗАДАЧА РАСШИРЕНИЯ
- Проанализируй существующие кластеры и найди пропущенные аспекты тематики
- Сгенерируй ТОЛЬКО НОВЫЕ кластеры, которые НЕ дублируют существующие
- Цель: добавить максимально возможное количество новых уникальных head-запросов (без искусственных лимитов)
- Фокус на пропущенных Parent Theme и недостающих запросах в существующих темах
- Генерируй столько новых кластеров, сколько нужно для полного покрытия новой тематики
- Обязательно учти новую тематику (если указана) и разрешённые типы: расширь список с учётом новой тематики/типов

{type_directives}

{minus_block}{region_block}
{fixed_rules}

ВАЖНО: НЕ повторяй существующие кластеры! Генерируй только новые, дополняющие покрытие."""

    try:
        # Параметры для GPT-5
        call_params = {
            "model": OPENAI_MODEL,
            "max_output_tokens": 8000,
            "input": [
                {"role": "user", "content": [{"type": "input_text", "text": expansion_prompt}]}
            ],
        }
        
        print("==================================================")
        print("EXPANDING TEMPLATE WITH GPT-5:")
        print("==================================================")
        print(f"Template: {template.name}")
        print(f"Existing clusters: {len(template.clusters)}")
        print(f"Target: 30-50 new clusters")
        print("==================================================")
        
        # Use unified ask_gpt5 wrapper
        response_text = await ask_gpt5(
            input_blocks=[
                {"role": "user", "content": [{"type": "input_text", "text": expansion_prompt}]}
            ],
            model=OPENAI_MODEL,
            max_output_tokens=12000,
        )
        
        print(f"GPT-5 expansion response length: {len(response_text)}")
        
        # Парсим ответ
        clusters = parse_gpt5_response(response_text)
        print(f"Parsed {len(clusters)} new clusters from GPT-5 expansion")
        
        return clusters
        
    except Exception as e:
        print(f"Error in template expansion: {e}")
        import traceback
        traceback.print_exc()
        return []
