import { useMemo } from 'react'
import type { Intent } from '../types'

export interface ValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  suggestions: string[]
  complexityScore: number
  estimatedTime: string
}

export interface TopicAnalysis {
  wordCount: number
  hasMultipleTopics: boolean
  topics: string[]
  isTooGeneric: boolean
  isTooSpecific: boolean
  suggestedIntents: Intent[]
  complexityLevel: 'low' | 'medium' | 'high'
}

export function analyzeTopic(topic: string): TopicAnalysis {
  const trimmed = topic.trim()
  const wordCount = trimmed.split(/\s+/).length
  const hasMultipleTopics = trimmed.includes(',') || trimmed.includes(';') || trimmed.includes('|')
  
  // Extract individual topics
  const topics = trimmed.split(/[,;|]/).map(t => t.trim()).filter(t => t.length > 0)
  
  // Check if too generic (common words)
  const genericWords = ['услуги', 'товары', 'продукты', 'компания', 'фирма', 'бизнес']
  const isTooGeneric = genericWords.some(word => 
    trimmed.toLowerCase().includes(word.toLowerCase())
  )
  
  // Check if too specific (very long, detailed)
  const isTooSpecific = wordCount > 8 && !hasMultipleTopics
  
  // Suggest intents based on topic content
  const suggestedIntents: Intent[] = []
  const topicLower = trimmed.toLowerCase()
  
  if (topicLower.includes('купить') || topicLower.includes('цена') || topicLower.includes('стоимость')) {
    suggestedIntents.push('commercial', 'price')
  }
  if (topicLower.includes('как') || topicLower.includes('что') || topicLower.includes('виды')) {
    suggestedIntents.push('informational')
  }
  if (topicLower.includes('ремонт') || topicLower.includes('установка') || topicLower.includes('обслуживание')) {
    suggestedIntents.push('service')
  }
  if (topicLower.includes('рядом') || topicLower.includes('адрес') || topicLower.includes('где')) {
    suggestedIntents.push('local')
  }
  if (topicLower.includes('срочно') || topicLower.includes('быстро') || topicLower.includes('24/7')) {
    suggestedIntents.push('urgent')
  }
  if (topicLower.includes('отзыв') || topicLower.includes('мнение') || topicLower.includes('рейтинг')) {
    suggestedIntents.push('reviews')
  }
  if (topicLower.includes('лучший') || topicLower.includes('сравнить') || topicLower.includes('топ')) {
    suggestedIntents.push('comparative')
  }
  if (topicLower.includes('как сделать') || topicLower.includes('инструкция') || topicLower.includes('самостоятельно')) {
    suggestedIntents.push('diy')
  }
  if (topicLower.includes('скачать') || topicLower.includes('документ') || topicLower.includes('схема')) {
    suggestedIntents.push('download')
  }
  if (topicLower.includes('параметр') || topicLower.includes('характеристик') || topicLower.includes('техническ')) {
    suggestedIntents.push('technical')
  }
  if (topicLower.includes('лицензи') || topicLower.includes('сертификат') || topicLower.includes('требовани')) {
    suggestedIntents.push('legal')
  }
  if (topicLower.includes('бренд') || topicLower.includes('марка') || topicLower.includes('производитель')) {
    suggestedIntents.push('brand')
  }
  if (topicLower.includes('официальный') || topicLower.includes('сайт') || topicLower.includes('контакт')) {
    suggestedIntents.push('navigational')
  }
  if (topicLower.includes('не работает') || topicLower.includes('сломался') || topicLower.includes('проблема')) {
    suggestedIntents.push('problem')
  }
  
  // Determine complexity level
  let complexityLevel: 'low' | 'medium' | 'high' = 'low'
  if (hasMultipleTopics || wordCount > 5) {
    complexityLevel = 'medium'
  }
  if (hasMultipleTopics && wordCount > 3) {
    complexityLevel = 'high'
  }
  
  return {
    wordCount,
    hasMultipleTopics,
    topics,
    isTooGeneric,
    isTooSpecific,
    suggestedIntents: [...new Set(suggestedIntents)],
    complexityLevel
  }
}

export function validateTopicAndIntents(
  topic: string, 
  selectedIntents: Intent[]
): ValidationResult {
  const analysis = analyzeTopic(topic)
  const errors: string[] = []
  const warnings: string[] = []
  const suggestions: string[] = []
  
  // Validation rules
  if (!topic.trim()) {
    errors.push('Тематика не может быть пустой')
  }
  
  if (analysis.wordCount < 2) {
    errors.push('Тематика слишком короткая. Рекомендуется минимум 2 слова')
  }
  
  if (analysis.isTooGeneric) {
    warnings.push('Тематика слишком общая. Рекомендуется добавить детализацию')
    suggestions.push('Попробуйте добавить конкретные детали: "ремонт окон в Москве", "установка дверей Rehau"')
  }
  
  if (analysis.isTooSpecific) {
    warnings.push('Тематика слишком детализированная. Может ограничить покрытие')
    suggestions.push('Попробуйте упростить или разделить на несколько тем через запятую')
  }
  
  if (selectedIntents.length === 0) {
    errors.push('Выберите хотя бы один тип запроса')
  }
  
  if (selectedIntents.length > 8) {
    warnings.push('Слишком много типов запросов. Рекомендуется 3-5 для оптимального результата')
  }
  
  // Suggest intents based on topic analysis
  if (analysis.suggestedIntents.length > 0) {
    const missingIntents = analysis.suggestedIntents.filter(intent => !selectedIntents.includes(intent))
    if (missingIntents.length > 0) {
      suggestions.push(`Рекомендуемые типы запросов: ${missingIntents.join(', ')}`)
    }
  }
  
  // Complexity scoring (0-100)
  let complexityScore = 0
  complexityScore += analysis.wordCount * 5
  complexityScore += analysis.hasMultipleTopics ? 20 : 0
  complexityScore += selectedIntents.length * 8
  complexityScore += analysis.isTooGeneric ? -10 : 0
  complexityScore += analysis.isTooSpecific ? 15 : 0
  
  complexityScore = Math.max(0, Math.min(100, complexityScore))
  
  // Estimate generation time
  let estimatedTime = '1-2 минуты'
  if (complexityScore > 70) {
    estimatedTime = '3-5 минут'
  } else if (complexityScore > 40) {
    estimatedTime = '2-3 минуты'
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    suggestions,
    complexityScore,
    estimatedTime
  }
}

export function useTopicValidation(topic: string, selectedIntents: Intent[]) {
  return useMemo(() => {
    return validateTopicAndIntents(topic, selectedIntents)
  }, [topic, selectedIntents])
}
