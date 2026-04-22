import React, { useState } from 'react'
import { Search, Filter, X, ChevronDown, ChevronUp } from 'lucide-react'
import { useFilterState, FILTER_PRESETS, type FilterState } from '../utils/filterUtils'
import type { UpperCluster, Intent } from '../types'

// Маппинг интентов на русский
const INTENT_DISPLAY_NAMES: Record<string, string> = {
  commercial: 'Коммерческие',
  informational: 'Информационные',
  service: 'Услуги',
  price: 'Ценовые',
  local: 'Локальные',
  urgent: 'Срочные',
  reviews: 'Отзывы',
  comparative: 'Сравнительные',
  diy: 'Сделай сам',
  download: 'Скачать',
  technical: 'Технические',
  legal: 'Юридические',
  brand: 'Брендовые',
  navigational: 'Навигационные',
  problem: 'Проблемные'
}

// Маппинг уровней спроса
const DEMAND_LEVEL_NAMES: Record<string, string> = {
  'High': 'Высокий',
  'Medium': 'Средний',
  'Low': 'Низкий'
}

interface Props {
  clusters: UpperCluster[]
  onFiltersChange: (filters: FilterState) => void
}

export default function EnhancedFilters({ clusters, onFiltersChange }: Props) {
  const { filters, updateFilter, resetFilters, applyPreset } = useFilterState()
  const [isExpanded, setIsExpanded] = useState(false)

  // Get unique values for dropdowns
  const parentThemes = Array.from(new Set(clusters.map(c => c.parent_theme).filter(Boolean)))
  const allIntents = Array.from(new Set(clusters.map(c => c.gpt_intent).filter(Boolean)))
  const allTags = Array.from(new Set(clusters.flatMap(c => c.tags || [])))
  const demandLevels = ['High', 'Medium', 'Low']

  // Notify parent of filter changes
  React.useEffect(() => {
    onFiltersChange(filters)
  }, [filters, onFiltersChange])

  const handleIntentToggle = (intent: string) => {
    const currentIntents = filters.selectedIntents
    const updatedIntents = currentIntents.includes(intent)
      ? currentIntents.filter(i => i !== intent)
      : [...currentIntents, intent]
    updateFilter('selectedIntents', updatedIntents)
  }

  const handleTagToggle = (tag: string) => {
    const currentTags = filters.selectedTags
    const updatedTags = currentTags.includes(tag)
      ? currentTags.filter(t => t !== tag)
      : [...currentTags, tag]
    updateFilter('selectedTags', updatedTags)
  }

  const activeFiltersCount = [
    filters.search,
    filters.parentTheme,
    filters.demandLevel,
    filters.selectedIntents.length > 0,
    filters.selectedTags.length > 0,
    filters.minQueryLength !== 2,
    filters.maxQueryLength !== 10,
    filters.groupByParentTheme,
    filters.showOnlyHighDemand,
    filters.showOnlyCommercial
  ].filter(Boolean).length

  return (
    <div className="bg-white rounded-xl mb-6">
      {/* Filter Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-slate-600" />
            <h3 className="font-semibold text-slate-800">Фильтры и поиск</h3>
            {activeFiltersCount > 0 && (
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full border border-blue-200">
                {activeFiltersCount} активных
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 px-3 py-1 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
            >
              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              {isExpanded ? 'Свернуть' : 'Развернуть'}
            </button>
            
            {activeFiltersCount > 0 && (
              <button
                onClick={resetFilters}
                className="flex items-center gap-1 px-3 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
              >
                <X size={14} />
                Сбросить
              </button>
            )}
          </div>
        </div>

        {/* Quick Presets */}
        <div className="mt-3 flex flex-wrap gap-2">
          {FILTER_PRESETS.map(preset => (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset.id)}
              className="px-3 py-1 text-xs bg-slate-100 text-slate-700 rounded-full hover:bg-slate-200 transition-colors"
              title={preset.description}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Поиск по названию
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                value={filters.search}
                onChange={(e) => updateFilter('search', e.target.value)}
                placeholder="Введите название кластера..."
                className="w-full pl-10 pr-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Parent Theme Filter */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Родительская тема
            </label>
            <select
              value={filters.parentTheme}
              onChange={(e) => updateFilter('parentTheme', e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Все темы</option>
              <option value="no-theme">Без темы</option>
              {parentThemes.map(theme => (
                <option key={theme} value={theme}>{theme}</option>
              ))}
            </select>
          </div>

          {/* Demand Level Filter */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Уровень спроса
            </label>
            <select
              value={filters.demandLevel}
              onChange={(e) => updateFilter('demandLevel', e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Все уровни</option>
              {demandLevels.map(level => (
                <option key={level} value={level}>
                  {DEMAND_LEVEL_NAMES[level]}
                </option>
              ))}
            </select>
          </div>

          {/* Intents Multi-select */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Интенты ({filters.selectedIntents.length} выбрано)
            </label>
            <div className="max-h-32 overflow-y-auto border border-slate-300 rounded-md p-2 space-y-1">
              {allIntents.map(intent => (
                <label key={intent} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={filters.selectedIntents.includes(intent)}
                    onChange={() => handleIntentToggle(intent)}
                    className="rounded border-slate-300 mr-2"
                  />
                  <span className="text-sm">{INTENT_DISPLAY_NAMES[intent] || intent}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Tags Multi-select */}
          {allTags.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Теги ({filters.selectedTags.length} выбрано)
              </label>
              <div className="max-h-32 overflow-y-auto border border-slate-300 rounded-md p-2 space-y-1">
                {allTags.slice(0, 20).map(tag => (
                  <label key={tag} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.selectedTags.includes(tag)}
                      onChange={() => handleTagToggle(tag)}
                      className="rounded border-slate-300 mr-2"
                    />
                    <span className="text-xs">{tag}</span>
                  </label>
                ))}
                {allTags.length > 20 && (
                  <div className="text-xs text-slate-400">
                    +{allTags.length - 20} еще тегов
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Query Length Range */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Длина запроса (слов): {filters.minQueryLength} - {filters.maxQueryLength}
            </label>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-slate-500">Минимум: {filters.minQueryLength}</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={filters.minQueryLength}
                  onChange={(e) => updateFilter('minQueryLength', Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">Максимум: {filters.maxQueryLength}</label>
                <input
                  type="range"
                  min="2"
                  max="15"
                  value={filters.maxQueryLength}
                  onChange={(e) => updateFilter('maxQueryLength', Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          {/* Quick Toggles */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Быстрые фильтры
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.groupByParentTheme}
                  onChange={(e) => updateFilter('groupByParentTheme', e.target.checked)}
                  className="rounded border-slate-300 mr-2"
                />
                <span className="text-sm">Группировать по Parent Theme</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.showOnlyHighDemand}
                  onChange={(e) => updateFilter('showOnlyHighDemand', e.target.checked)}
                  className="rounded border-slate-300 mr-2"
                />
                <span className="text-sm">Только высокий спрос</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.showOnlyCommercial}
                  onChange={(e) => updateFilter('showOnlyCommercial', e.target.checked)}
                  className="rounded border-slate-300 mr-2"
                />
                <span className="text-sm">Только коммерческие</span>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

