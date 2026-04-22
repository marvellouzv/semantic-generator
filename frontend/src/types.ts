export type Intent = 
  | 'commercial'      // Коммерческие: купить, заказать
  | 'informational'   // Информационные: что такое, как работает  
  | 'service'         // Сервисные: ремонт, установка
  | 'price'           // Ценовые: стоимость, расценки
  | 'navigational'    // Навигационные: найти компанию
  | 'brand'           // Брендовые: конкретные марки
  | 'diy'             // Своими руками: инструкции
  | 'download'        // Скачать: файлы, документы
  | 'comparative'     // Сравнительные: лучший, рейтинг
  | 'problem'         // Проблемные: не работает, сломался
  | 'local'           // Локальные: рядом, в городе
  | 'urgent'          // Срочные: быстро, экстренно
  | 'reviews'         // Отзывы: мнения, опыт
  | 'legal'           // Правовые: лицензии, документы
  | 'technical'       // Технические: характеристики, спецификации

// Limits removed - no restrictions for maximum coverage

export interface UpperCluster {
  cluster_id: string
  name: string
  intent_mix: Intent[]
  seed_examples?: string[]
  notes?: string
  demand_level?: string    // High/Medium/Low от GPT-5
  parent_category?: string // Родительская категория (тип запроса из выбранных пользователем)
  parent_theme?: string    // Parent Theme от GPT-5
  gpt_intent?: string      // Исходный интент от GPT-5
}

export interface UpperGraph {
  topic: string
  locale: string
  intents_applied: Intent[]
  clusters: UpperCluster[]
}

export interface UpperGraphRequest {
  topic: string
  locale: string
  intents: Intent[]
  brand_whitelist?: string[]  // Список брендов для брендовых запросов
  template_id?: string  // Для режима дополнения шаблона
  bulk_queries?: string[]  // Для массовой загрузки запросов
  minus_words?: string[]  // Минус-слова (запрещённые слова/фразы)
  regions?: string[]      // Регионы для локальных запросов (можно несколько)
}

export interface ExportRequest {
  format: 'xlsx' | 'csv'
  data: any  // Упрощенный тип для экспорта
}

// Типы для системы шаблонов
export interface ClusterTemplate {
  id: string
  name: string
  description: string
  topic: string
  locale: string
  intents_applied: Intent[]
  clusters: UpperCluster[]
  created_at: string
  updated_at: string
  cluster_count: number
}

export interface CreateTemplateRequest {
  name: string
  description: string
  upper_graph: UpperGraph
}

export interface TemplateListResponse {
  templates: ClusterTemplate[]
}
