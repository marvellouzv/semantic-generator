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
import { Download, Filter, Search, ChevronUp, ChevronDown } from 'lucide-react'
import type { ExpandedQueries, QueryItem, Intent } from '../types'
import { apiService } from '../api'

interface Props {
  expandedQueries: ExpandedQueries
  onBack: () => void
}

interface FlatQuery extends QueryItem {
  cluster_id: string
  cluster_name: string
}

export default function ExpansionScreen({ expandedQueries, onBack }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [selectedIntents, setSelectedIntents] = useState<Intent[]>([])
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [minQueryLength, setMinQueryLength] = useState(2)
  const [maxQueryLength, setMaxQueryLength] = useState(10)
  const [showFilters, setShowFilters] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  // Flatten queries for table display
  const flatQueries: FlatQuery[] = useMemo(() => {
    const queries: FlatQuery[] = []
    expandedQueries.expanded.forEach(cluster => {
      cluster.queries.forEach(query => {
        queries.push({
          ...query,
          cluster_id: cluster.cluster_id,
          cluster_name: cluster.cluster_name
        })
      })
    })
    return queries
  }, [expandedQueries])

  // Apply filters
  const filteredQueries = useMemo(() => {
    return flatQueries.filter(query => {
      const wordCount = query.q.split(' ').length
      
      // Length filter
      if (wordCount < minQueryLength || wordCount > maxQueryLength) {
        return false
      }
      
      // Intent filter
      if (selectedIntents.length > 0 && !selectedIntents.includes(query.intent)) {
        return false
      }
      
      // Tags filter
      if (selectedTags.length > 0) {
        const queryTags = query.tags || []
        const hasSelectedTag = selectedTags.some(tag => queryTags.includes(tag))
        if (!hasSelectedTag) {
          return false
        }
      }
      
      // Global search filter
      if (globalFilter && !query.q.toLowerCase().includes(globalFilter.toLowerCase())) {
        return false
      }
      
      return true
    })
  }, [flatQueries, minQueryLength, maxQueryLength, selectedIntents, selectedTags, globalFilter])

  const columnHelper = createColumnHelper<FlatQuery>()

  const columns = useMemo(() => [
    columnHelper.accessor('q', {
      header: 'Запрос',
      cell: ({ getValue }) => (
        <span className="font-medium">{getValue()}</span>
      )
    }),
    columnHelper.accessor('cluster_name', {
      header: 'Кластер',
      cell: ({ getValue }) => (
        <span className="text-sm text-gray-600">{getValue()}</span>
      )
    }),
    columnHelper.accessor('intent', {
      header: 'Интент',
      cell: ({ getValue }) => (
        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
          {getValue()}
        </span>
      )
    }),
    columnHelper.accessor('tags', {
      header: 'Теги',
      cell: ({ getValue }) => {
        const tags = getValue() || []
        return (
          <div className="flex flex-wrap gap-1">
            {tags.slice(0, 3).map((tag, idx) => (
              <span
                key={idx}
                className="px-1 py-0.5 bg-gray-100 text-gray-700 text-xs rounded"
              >
                {tag}
              </span>
            ))}
            {tags.length > 3 && (
              <span className="text-xs text-gray-400">+{tags.length - 3}</span>
            )}
          </div>
        )
      }
    }),
    columnHelper.display({
      id: 'word_count',
      header: 'Слов',
      cell: ({ row }) => (
        <span className="text-sm text-gray-500">
          {row.original.q.split(' ').length}
        </span>
      )
    })
  ], [])

  const table = useReactTable({
    data: filteredQueries,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })


  const handleExport = async (format: 'xlsx' | 'csv') => {
    setIsExporting(true)
    try {
      const blob = await apiService.exportData({
        format,
        data: expandedQueries
      })
      
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `semantic_queries.${format}`
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

  const uniqueIntents = Array.from(new Set(flatQueries.map(q => q.intent)))
  const uniqueTags = Array.from(new Set(flatQueries.flatMap(q => q.tags || [])))

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Расширенные запросы</h1>
            <p className="text-gray-600">
              Тема: <span className="font-medium">{expandedQueries.topic}</span> | 
              Всего запросов: <span className="font-medium">{flatQueries.length}</span> |
              Показано: <span className="font-medium">{filteredQueries.length}</span>
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={onBack}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Назад
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center gap-2"
            >
              <Filter size={16} />
              Фильтры
            </button>
            <div className="relative">
              <button
                disabled={isExporting}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                onClick={() => handleExport('xlsx')}
              >
                <Download size={16} />
                {isExporting ? 'Экспорт...' : 'XLSX'}
              </button>
            </div>
            <button
              disabled={isExporting}
              onClick={() => handleExport('csv')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              CSV
            </button>
          </div>
        </div>
      </div>

      {showFilters && (
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <h3 className="font-semibold mb-4">Фильтры</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Поиск по тексту
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  value={globalFilter}
                  onChange={(e) => setGlobalFilter(e.target.value)}
                  placeholder="Введите текст для поиска..."
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Минимум слов: {minQueryLength}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={minQueryLength}
                onChange={(e) => setMinQueryLength(Number(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Максимум слов: {maxQueryLength}
              </label>
              <input
                type="range"
                min="2"
                max="15"
                value={maxQueryLength}
                onChange={(e) => setMaxQueryLength(Number(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Интенты
              </label>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {uniqueIntents.map(intent => (
                  <label key={intent} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedIntents.includes(intent)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIntents(prev => [...prev, intent])
                        } else {
                          setSelectedIntents(prev => prev.filter(i => i !== intent))
                        }
                      }}
                      className="rounded border-gray-300 mr-2"
                    />
                    <span className="text-sm">{intent}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Теги ({uniqueTags.length})
              </label>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {uniqueTags.slice(0, 15).map(tag => (
                  <label key={tag} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedTags.includes(tag)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTags(prev => [...prev, tag])
                        } else {
                          setSelectedTags(prev => prev.filter(t => t !== tag))
                        }
                      }}
                      className="rounded border-gray-300 mr-2"
                    />
                    <span className="text-xs">{tag}</span>
                  </label>
                ))}
                {uniqueTags.length > 15 && (
                  <div className="text-xs text-gray-400">
                    +{uniqueTags.length - 15} еще
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => {
                setGlobalFilter('')
                setSelectedIntents([])
                setSelectedTags([])
                setMinQueryLength(2)
                setMaxQueryLength(10)
              }}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Сбросить фильтры
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Запросы ({filteredQueries.length})
            </h2>
          </div>
        </div>

        <div className="overflow-hidden">
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
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
                {table.getRowModel().rows.map(row => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-4 py-4 whitespace-nowrap text-sm">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
