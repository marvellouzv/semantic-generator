import React, { useState, useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
  ColumnFiltersState
} from '@tanstack/react-table'
import { ChevronUp, ChevronDown, Edit2, Trash2, Plus, Save, Download, BarChart3 } from 'lucide-react'
import type { UpperGraph, UpperCluster, Intent, UpperGraphRequest } from '../types'
import apiService from '../api'
import ClusterDashboard from './ClusterDashboard'
import EnhancedFilters from './EnhancedFilters'
import ExportDialog from './ExportDialog'
import MobileClusterCard from './MobileClusterCard'
import { useFilterState, type FilterState } from '../utils/filterUtils'

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
  upperGraph: UpperGraph
  setupData?: UpperGraphRequest
  onClustersUpdate: (clusters: UpperCluster[]) => void
  onProceed: (selectedClusters: string[]) => void
  loading: boolean
}

export default function UpperReviewScreen({ upperGraph, setupData, onClustersUpdate, onProceed, loading }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [selectedClusters, setSelectedClusters] = useState<string[]>(
    upperGraph.clusters.map(c => c.cluster_id)
  )
  const [editingCluster, setEditingCluster] = useState<string | null>(null)
  const [editedName, setEditedName] = useState('')
  const [additionalRequirements, setAdditionalRequirements] = useState('')
  const [expandedQueries, setExpandedQueries] = useState<any[]>([])
  const [isExpanding, setIsExpanding] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [showDashboard, setShowDashboard] = useState(true)
  const [currentFilters, setCurrentFilters] = useState<FilterState | null>(null)
  const [showExportDialog, setShowExportDialog] = useState(false)

  const columnHelper = createColumnHelper<UpperCluster>()

  // Apply filters to clusters
  const filteredClusters = useMemo(() => {
    if (!currentFilters) return upperGraph.clusters

    return upperGraph.clusters.filter(cluster => {
      // Search filter
      if (currentFilters.search && !cluster.name.toLowerCase().includes(currentFilters.search.toLowerCase())) {
        return false
      }

      // Parent theme filter
      if (currentFilters.parentTheme) {
        if (currentFilters.parentTheme === 'no-theme' && cluster.parent_theme) {
          return false
        }
        if (currentFilters.parentTheme !== 'no-theme' && cluster.parent_theme !== currentFilters.parentTheme) {
          return false
        }
      }

      // Demand level filter
      if (currentFilters.demandLevel && cluster.demand_level !== currentFilters.demandLevel) {
        return false
      }

      // Intent filter
      if (currentFilters.selectedIntents.length > 0) {
        const clusterIntent = cluster.gpt_intent || ''
        const normalizedIntent = clusterIntent === 'коммерческие' ? 'commercial' : 
                                clusterIntent === 'информационные' ? 'informational' :
                                clusterIntent === 'локальные' ? 'local' :
                                clusterIntent === 'отзывы' ? 'reviews' :
                                clusterIntent === 'ценовые' ? 'price' :
                                clusterIntent === 'срочные' ? 'urgent' :
                                clusterIntent === 'сравнительные' ? 'comparative' : clusterIntent
        
        if (!currentFilters.selectedIntents.includes(normalizedIntent)) {
          return false
        }
      }

      // Tags filter
      if (currentFilters.selectedTags.length > 0) {
        const clusterTags = cluster.tags || []
        const hasSelectedTag = currentFilters.selectedTags.some(tag => clusterTags.includes(tag))
        if (!hasSelectedTag) {
          return false
        }
      }

      // Query length filter (based on seed examples)
      const avgWordCount = cluster.seed_examples 
        ? cluster.seed_examples.reduce((sum, example) => sum + example.split(' ').length, 0) / cluster.seed_examples.length
        : cluster.name.split(' ').length

      if (avgWordCount < currentFilters.minQueryLength || avgWordCount > currentFilters.maxQueryLength) {
        return false
      }

      // Quick toggles
      if (currentFilters.showOnlyHighDemand && cluster.demand_level !== 'High') {
        return false
      }

      if (currentFilters.showOnlyCommercial) {
        const clusterIntent = cluster.gpt_intent || ''
        if (clusterIntent !== 'commercial' && clusterIntent !== 'коммерческие') {
          return false
        }
      }

      return true
    })
  }, [upperGraph.clusters, currentFilters])

  const columns = useMemo(() => [
    columnHelper.display({
      id: 'select',
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllRowsSelected()}
          onChange={table.getToggleAllRowsSelectedHandler()}
          className="rounded border-gray-300"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selectedClusters.includes(row.original.cluster_id)}
          onChange={(e) => {
            const clusterId = row.original.cluster_id
            setSelectedClusters(prev => 
              e.target.checked 
                ? [...prev, clusterId]
                : prev.filter(id => id !== clusterId)
            )
          }}
          className="rounded border-gray-300"
        />
      ),
    }),
    columnHelper.accessor('name', {
      header: 'Название кластера',
      cell: ({ row, getValue }) => {
        const isEditing = editingCluster === row.original.cluster_id
        const value = getValue()
        
        return isEditing ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              className="flex-1 p-1 border border-gray-300 rounded text-sm"
              autoFocus
            />
            <button
              onClick={() => {
                const updatedClusters = upperGraph.clusters.map(c =>
                  c.cluster_id === row.original.cluster_id
                    ? { ...c, name: editedName }
                    : c
                )
                onClustersUpdate(updatedClusters)
                setEditingCluster(null)
              }}
              className="p-1 text-green-600 hover:text-green-800"
            >
              ✓
            </button>
            <button
              onClick={() => setEditingCluster(null)}
              className="p-1 text-gray-600 hover:text-gray-800"
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between group">
            <span className="font-medium">{value}</span>
            <button
              onClick={() => {
                setEditingCluster(row.original.cluster_id)
                setEditedName(value)
              }}
              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-gray-600"
            >
              <Edit2 size={14} />
            </button>
          </div>
        )
      }
    }),
    columnHelper.accessor('gpt_intent', {
      header: 'Интент (GPT)',
      cell: ({ getValue }) => {
        const gptIntent = (getValue() || '').toString().toLowerCase()
        const displayName =
          gptIntent === 'commercial' ? 'Коммерческий' :
          gptIntent === 'informational' ? 'Информационный' :
          gptIntent === 'unknown' ? 'Не определено' :
          getValue()

        const intentColorMap: Record<string, string> = {
          commercial: 'bg-blue-100 text-blue-800',
          informational: 'bg-green-100 text-green-800',
          unknown: 'bg-gray-100 text-gray-700'
        }

        const color = intentColorMap[gptIntent as keyof typeof intentColorMap] || 'bg-gray-100 text-gray-600'

        return getValue() ? (
          <span className={`px-2 py-1 text-xs rounded-full ${color}`}>
            {displayName}
          </span>
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )
      }
    }),
    columnHelper.accessor('demand_level', {
      header: 'Уровень спроса',
      cell: ({ getValue }) => {
        const level = getValue()
        const displayName = DEMAND_LEVEL_NAMES[level as keyof typeof DEMAND_LEVEL_NAMES] || level
        
        const levelColorMap: Record<string, string> = {
          'Высокий': 'bg-red-100 text-red-800',
          'High': 'bg-red-100 text-red-800',
          'Средний': 'bg-yellow-100 text-yellow-800',
          'Medium': 'bg-yellow-100 text-yellow-800',
          'Низкий': 'bg-gray-100 text-gray-800',
          'Low': 'bg-gray-100 text-gray-800'
        }
        
        const color = levelColorMap[level as keyof typeof levelColorMap] || 'bg-gray-100 text-gray-600'
        
        return level ? (
          <span className={`px-2 py-1 text-xs rounded-full ${color}`}>
            {displayName}
          </span>
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )
      }
    }),
    columnHelper.accessor('parent_category', {
      header: 'Группа (выбранный тип)',
      cell: ({ getValue }) => {
        const category = getValue()
        return category ? (
          <span className="text-sm text-blue-700 font-medium">
            {category}
          </span>
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )
      }
    }),
    columnHelper.accessor('parent_theme', {
      header: 'Родительская тема',
      cell: ({ getValue }) => {
        const theme = getValue()
        return theme ? (
          <span className="text-sm text-slate-700 font-medium">
            {theme}
          </span>
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )
      }
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Действия',
      cell: ({ row }) => (
        <button
          onClick={() => {
            const updatedClusters = upperGraph.clusters.filter(
              c => c.cluster_id !== row.original.cluster_id
            )
            onClustersUpdate(updatedClusters)
            setSelectedClusters(prev => prev.filter(id => id !== row.original.cluster_id))
          }}
          className="p-1 text-red-400 hover:text-red-600"
        >
          <Trash2 size={14} />
        </button>
      )
    })
  ], [upperGraph.clusters, selectedClusters, editingCluster, editedName, onClustersUpdate])

  const table = useReactTable({
    data: filteredClusters,
    columns,
    state: {
      sorting,
      columnFilters,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const handleExpandQueries = async () => {
    if (!additionalRequirements.trim()) {
      alert('Пожалуйста, введите дополнительные требования')
      return
    }

    setIsExpanding(true)
    try {
      // Собираем существующие запросы из кластеров
      const existingQueries = upperGraph.clusters.flatMap(c => c.seed_examples || [])
      
      // Собираем родительские темы из кластеров
      const parentThemes = [...new Set(upperGraph.clusters.map(c => c.parent_theme).filter(Boolean))]
      
      // Получаем разрешенные типы из интентов
      const allowedTypes = upperGraph.intents_applied || []
      
      console.log('Sending expand request:', {
        topic: upperGraph.topic,
        locale: upperGraph.locale,
        additional_requirements: additionalRequirements,
        existing_queries: existingQueries,
        parent_themes: parentThemes,
        allowed_types: allowedTypes
      })
      
      const response = await apiService.expandQueries({
        topic: upperGraph.topic,
        locale: upperGraph.locale,
        additional_requirements: additionalRequirements,
        existing_queries: existingQueries,
        parent_themes: parentThemes,
        allowed_types: allowedTypes,
        minus_words: setupData?.minus_words || [],
        regions: setupData?.regions || []
      })
      
      setExpandedQueries(response.expanded_queries)
      alert(`Сгенерировано ${response.expanded_queries.length} дополнительных запросов!`)
    } catch (error) {
      console.error('Ошибка расширения запросов:', error)
      alert('Ошибка при расширении запросов. Проверьте консоль для деталей.')
    } finally {
      setIsExpanding(false)
    }
  }

  const handleAddToTable = () => {
    if (expandedQueries.length === 0) {
      alert('Нет запросов для добавления')
      return
    }

    // Конвертируем сгенерированные запросы в кластеры
    const newClusters: UpperCluster[] = expandedQueries.map((query, index) => ({
      cluster_id: `generated_${Date.now()}_${index}`,
      name: query.query,
      intent_mix: [query.intent as Intent],
      gpt_intent: query.intent as Intent,
      demand_level: query.demand_level as 'High' | 'Medium' | 'Low',
      parent_category: query.intent ? (INTENT_DISPLAY_NAMES[query.intent as keyof typeof INTENT_DISPLAY_NAMES] || query.intent) : undefined,
      parent_theme: query.parent_theme,
      seed_examples: [query.query], // Используем сам запрос как seed example
      tags: query.tags || []
    }))

    // Добавляем новые кластеры к существующим
    const updatedClusters = [...upperGraph.clusters, ...newClusters]
    
    // Обновляем состояние
    onClustersUpdate(updatedClusters)
    
    // Добавляем новые кластеры к выбранным
    const newClusterIds = newClusters.map(c => c.cluster_id)
    setSelectedClusters(prev => [...prev, ...newClusterIds])
    
    // Очищаем сгенерированные запросы
    setExpandedQueries([])
    setAdditionalRequirements('')
    
    alert(`Добавлено ${newClusters.length} новых кластеров в таблицу!`)
  }

  const handleProceed = () => {
    const selectedClusterObjects = upperGraph.clusters.filter(c => 
      selectedClusters.includes(c.cluster_id)
    )
    onClustersUpdate(selectedClusterObjects)
    onProceed(selectedClusters)
  }

  const handleExportClusters = async (format: 'xlsx' | 'csv') => {
    setIsExporting(true)
    try {
      const blob = await apiService.exportClusters({
        format,
        clusters: upperGraph.clusters
      })
      
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `clusters.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Ошибка экспорта. Попробуйте еще раз.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 pb-28">
      <div className="mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-4 gap-4">
          <div className="flex-1">
            <h1 className="text-2xl md:text-3xl font-bold mb-2">Обзор кластеров</h1>
            <p className="text-sm md:text-base text-gray-600">
              Тема: <span className="font-medium">{upperGraph.topic}</span>
            </p>
            <p className="text-sm md:text-base text-gray-600">
              Интенты: <span className="font-medium">{upperGraph.intents_applied.map(intent => INTENT_DISPLAY_NAMES[intent as keyof typeof INTENT_DISPLAY_NAMES] || intent).join(', ')}</span>
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <button
              onClick={() => setShowDashboard(!showDashboard)}
              className="flex items-center justify-center gap-2 px-3 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors text-sm"
            >
              <BarChart3 size={16} />
              <span className="hidden sm:inline">
                {showDashboard ? 'Скрыть аналитику' : 'Показать аналитику'}
              </span>
              <span className="sm:hidden">
                {showDashboard ? 'Скрыть' : 'Аналитика'}
              </span>
            </button>
          </div>
        </div>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-800">
            📊 <strong>GPT-5 таблица:</strong> Показаны данные прямо из GPT-5 ответа - Head Query, Intent, Demand Level, Parent Theme
          </p>
        </div>
      </div>

      {/* Dashboard */}
      {showDashboard && <ClusterDashboard upperGraph={upperGraph} />}

      {/* Enhanced Filters */}
      <EnhancedFilters 
        clusters={upperGraph.clusters}
        onFiltersChange={setCurrentFilters}
      />

      <div className="bg-white rounded-xl">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <h2 className="text-lg font-semibold">
                  Кластеры ({filteredClusters.length}{currentFilters ? ` из ${upperGraph.clusters.length}` : ''})
                </h2>
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4 text-sm text-gray-500">
                  <span>Выбрано: {selectedClusters.length}</span>
                  <span>
                    Тем: {Array.from(new Set(filteredClusters.map(c => c.parent_theme).filter(Boolean))).length}
                  </span>
                  <span>
                    Высокий: {filteredClusters.filter(c => c.demand_level === 'High').length} |
                    Средний: {filteredClusters.filter(c => c.demand_level === 'Medium').length} |
                    Низкий: {filteredClusters.filter(c => c.demand_level === 'Low').length}
                  </span>
                  <span>
                    Коммерческие: {filteredClusters.filter(c => {
                      const intent = c.gpt_intent || ''
                      return intent === 'commercial' || intent === 'коммерческие'
                    }).length} |
                    Информационные: {filteredClusters.filter(c => {
                      const intent = c.gpt_intent || ''
                      return intent === 'informational' || intent === 'информационные'
                    }).length}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              {currentFilters && (
                <div className="text-sm text-gray-500 text-center sm:text-left">
                  Фильтры активны
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Мобильная версия - карточки */}
        <div className="block md:hidden">
          {table.getRowModel().rows.map(row => (
            <MobileClusterCard
              key={row.id}
              cluster={row.original}
              isSelected={selectedClusters.includes(row.original.cluster_id)}
              onSelect={(clusterId, selected) => {
                if (selected) {
                  setSelectedClusters(prev => [...prev, clusterId])
                } else {
                  setSelectedClusters(prev => prev.filter(id => id !== clusterId))
                }
              }}
              onEdit={(clusterId) => {
                const cluster = row.original
                setEditingCluster(clusterId)
                setEditedName(cluster.name)
              }}
              onDelete={(clusterId) => {
                const updatedClusters = upperGraph.clusters.filter(c => c.cluster_id !== clusterId)
                onClustersUpdate(updatedClusters)
                setSelectedClusters(prev => prev.filter(id => id !== clusterId))
              }}
            />
          ))}
        </div>
        
        {/* Десктопная версия - таблица */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full">
            <thead>
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id} className="border-b border-gray-200 bg-gray-50">
                  {headerGroup.headers.map(header => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {header.isPlaceholder ? null : (
                        <div
                          className={`flex items-center gap-2 ${
                            header.column.getCanSort() ? 'cursor-pointer select-none' : ''
                          }`}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getCanSort() && (
                            <span className="text-gray-400">
                              {header.column.getIsSorted() === 'desc' ? (
                                <ChevronDown size={14} />
                              ) : header.column.getIsSorted() === 'asc' ? (
                                <ChevronUp size={14} />
                              ) : (
                                <ChevronUp size={14} className="opacity-30" />
                              )}
                            </span>
                          )}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {table.getRowModel().rows.map(row => {
                const demandLevel = row.original.demand_level
                const rowColorClass = {
                  'High': 'bg-red-50 hover:bg-red-100',
                  'Medium': 'bg-yellow-50 hover:bg-yellow-100', 
                  'Low': 'bg-gray-50 hover:bg-gray-100'
                }[demandLevel as keyof typeof rowColorClass] || 'hover:bg-gray-50'
                
                return (
                  <tr key={row.id} className={rowColorClass}>
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-4 py-4 whitespace-nowrap text-sm">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Секция расширения запросов — переносим вниз, под таблицу */}
      <div className="mt-6 mb-6 bg-white rounded-xl p-6">
        <h2 className="text-xl font-semibold tracking-tight mb-4">Расширение запросов</h2>
        <p className="text-gray-600 mb-4">
          Введите дополнительные требования для генерации дополнительных запросов с помощью GPT-5-mini
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Дополнительные требования
            </label>
            <textarea
              value={additionalRequirements}
              onChange={(e) => setAdditionalRequirements(e.target.value)}
              placeholder="Например: добавь запросы про ремонт окон в Москве, цены на услуги, сравнение компаний, отзывы клиентов..."
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={3}
            />
          </div>
          
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <button
              onClick={handleExpandQueries}
              disabled={isExpanding || !additionalRequirements.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isExpanding ? 'Генерация...' : 'Сгенерировать запросы'}
            </button>
            
            {expandedQueries.length > 0 && (
              <span className="text-sm text-green-600 font-medium">
                ✓ Сгенерировано {expandedQueries.length} запросов
              </span>
            )}
          </div>
          
          {expandedQueries.length > 0 && (
            <div className="mt-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                <h3 className="text-lg font-medium">Сгенерированные запросы:</h3>
                <button
                  onClick={handleAddToTable}
                  className="px-4 py-2 bg-slate-700 text-white rounded-md hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
                >
                  <Plus size={16} />
                  Добавить в таблицу
                </button>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 max-h-60 overflow-y-auto">
                <div className="space-y-2">
                  {expandedQueries.map((query, index) => (
                    <div key={index} className="bg-white p-3 rounded border text-sm">
                      <div className="font-medium text-gray-900">{query.query}</div>
                      <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-gray-500">
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">{query.intent}</span>
                        <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded">{query.demand_level}</span>
                        <span className="text-gray-600">{query.parent_theme}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Export Dialog */}
      {showExportDialog && (
        <ExportDialog
          clusters={upperGraph.clusters}
          upperGraph={upperGraph}
          filteredClusters={currentFilters ? filteredClusters : undefined}
          onClose={() => setShowExportDialog(false)}
        />
      )}

      {/* Sticky bottom action bar */}
      <div className="sticky bottom-0 z-30">
        <div className="bg-white/95 backdrop-blur border border-gray-200 rounded-xl shadow-sm px-4 py-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="text-sm text-gray-500">
              {selectedClusters.length} из {filteredClusters.length} кластеров выбрано
            </div>
            
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <button
                onClick={() => setShowExportDialog(true)}
                disabled={isExporting}
                className="px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                <Download size={16} />
                {isExporting ? 'Экспорт...' : 'Экспорт'}
              </button>
              
              <button
                onClick={async () => {
                  const templateName = prompt('Введите название шаблона:')
                  if (templateName) {
                    try {
                      const template = await apiService.createTemplate({
                        name: templateName,
                        description: `Шаблон для темы "${upperGraph.topic}" с интентами: ${upperGraph.intents_applied.map(intent => INTENT_DISPLAY_NAMES[intent as keyof typeof INTENT_DISPLAY_NAMES] || intent).join(', ')}`,
                        upper_graph: upperGraph
                      })
                      alert(`Шаблон "${templateName}" успешно сохранен! ID: ${template.id}`)
                    } catch (error) {
                      console.error('Ошибка сохранения шаблона:', error)
                      alert('Ошибка при сохранении шаблона. Проверьте консоль для деталей.')
                    }
                  }
                }}
                className="px-4 py-2 bg-slate-700 text-white rounded-md hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
              >
                <Save size={16} />
                Сохранить как шаблон
              </button>
              
              <button
                onClick={handleProceed}
                disabled={loading || selectedClusters.length === 0}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Расширение...' : `Расширить выбранные (${selectedClusters.length})`}
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}
