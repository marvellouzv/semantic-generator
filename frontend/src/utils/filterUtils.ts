import { useState, useEffect } from 'react'

export interface FilterState {
  search: string
  parentTheme: string
  demandLevel: string
  selectedIntents: string[]
  selectedTags: string[]
  minQueryLength: number
  maxQueryLength: number
  groupByParentTheme: boolean
  showOnlyHighDemand: boolean
  showOnlyCommercial: boolean
}

const DEFAULT_FILTERS: FilterState = {
  search: '',
  parentTheme: '',
  demandLevel: '',
  selectedIntents: [],
  selectedTags: [],
  minQueryLength: 2,
  maxQueryLength: 10,
  groupByParentTheme: false,
  showOnlyHighDemand: false,
  showOnlyCommercial: false
}

const STORAGE_KEY = 'semantic-generator-filters'

export function useFilterState() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)

  // Load filters from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        setFilters({ ...DEFAULT_FILTERS, ...parsed })
      }
    } catch (error) {
      console.warn('Failed to load filters from localStorage:', error)
    }
  }, [])

  // Save filters to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filters))
    } catch (error) {
      console.warn('Failed to save filters to localStorage:', error)
    }
  }, [filters])

  const updateFilter = <K extends keyof FilterState>(
    key: K,
    value: FilterState[K]
  ) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS)
  }

  const applyPreset = (preset: 'high-demand-commercial' | 'informational-only' | 'no-parent-theme' | 'all') => {
    switch (preset) {
      case 'high-demand-commercial':
        setFilters(prev => ({
          ...prev,
          showOnlyHighDemand: true,
          selectedIntents: ['commercial'],
          demandLevel: 'High'
        }))
        break
      case 'informational-only':
        setFilters(prev => ({
          ...prev,
          selectedIntents: ['informational'],
          demandLevel: '',
          showOnlyHighDemand: false,
          showOnlyCommercial: false
        }))
        break
      case 'no-parent-theme':
        setFilters(prev => ({
          ...prev,
          parentTheme: 'no-theme',
          demandLevel: '',
          showOnlyHighDemand: false,
          showOnlyCommercial: false
        }))
        break
      case 'all':
        resetFilters()
        break
    }
  }

  return {
    filters,
    updateFilter,
    resetFilters,
    applyPreset
  }
}

export const FILTER_PRESETS = [
  {
    id: 'high-demand-commercial' as const,
    label: 'Высокий спрос + Коммерческие',
    description: 'Показать только коммерческие кластеры с высоким спросом'
  },
  {
    id: 'informational-only' as const,
    label: 'Все информационные',
    description: 'Показать только информационные кластеры'
  },
  {
    id: 'no-parent-theme' as const,
    label: 'Без Parent Theme',
    description: 'Показать кластеры без родительской темы'
  },
  {
    id: 'all' as const,
    label: 'Сбросить фильтры',
    description: 'Показать все кластеры'
  }
]
