import React, { useState, useEffect } from 'react'
import { Search, Edit3, Trash2, Copy, Eye, Tag, Calendar, Hash, Filter } from 'lucide-react'
import type { ClusterTemplate, UpperGraph } from '../types'
import apiService from '../api'

interface Props {
  onTemplateLoad: (upperGraph: UpperGraph) => void
  onTemplateEdit: (template: ClusterTemplate) => void
  onClose: () => void
  showTemplateManager?: boolean
}

interface TemplateFilters {
  search: string
  tags: string[]
  dateRange: 'all' | 'week' | 'month' | 'year'
  sortBy: 'name' | 'date' | 'clusters'
}

export default function TemplateManager({ onTemplateLoad, onTemplateEdit, onClose }: Props) {
  const [templates, setTemplates] = useState<ClusterTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<TemplateFilters>({
    search: '',
    tags: [],
    dateRange: 'all',
    sortBy: 'date'
  })
  const [showPreview, setShowPreview] = useState<ClusterTemplate | null>(null)
  const [showEditDialog, setShowEditDialog] = useState<ClusterTemplate | null>(null)

  // Load templates when component mounts
  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      console.log('TemplateManager: Loading templates...')
      const response = await apiService.listTemplates()
      console.log('TemplateManager: Templates loaded:', response.templates.length)
      setTemplates(response.templates)
    } catch (error) {
      console.error('Ошибка загрузки шаблонов:', error)
    } finally {
      setLoading(false)
    }
  }

  // Filter and sort templates
  const filteredTemplates = React.useMemo(() => {
    let filtered = templates

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      filtered = filtered.filter(t => 
        t.name.toLowerCase().includes(searchLower) ||
        t.topic.toLowerCase().includes(searchLower) ||
        t.description.toLowerCase().includes(searchLower)
      )
    }

    // Tags filter
    if (filters.tags.length > 0) {
      filtered = filtered.filter(t => 
        filters.tags.some(tag => t.tags?.includes(tag))
      )
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date()
      const templateDate = new Date()
      
      switch (filters.dateRange) {
        case 'week':
          templateDate.setDate(now.getDate() - 7)
          break
        case 'month':
          templateDate.setMonth(now.getMonth() - 1)
          break
        case 'year':
          templateDate.setFullYear(now.getFullYear() - 1)
          break
      }
      
      filtered = filtered.filter(t => new Date(t.created_at) >= templateDate)
    }

    // Sort
    filtered.sort((a, b) => {
      switch (filters.sortBy) {
        case 'name':
          return a.name.localeCompare(b.name)
        case 'clusters':
          return b.cluster_count - a.cluster_count
        case 'date':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      }
    })

    return filtered
  }, [templates, filters])

  // Get unique tags
  const allTags = React.useMemo(() => {
    const tags = new Set<string>()
    templates.forEach(t => {
      t.tags?.forEach(tag => tags.add(tag))
    })
    return Array.from(tags).sort()
  }, [templates])

  const handleDelete = async (template: ClusterTemplate) => {
    if (!confirm(`Удалить шаблон "${template.name}"?`)) return

    try {
      await apiService.deleteTemplate(template.id)
      setTemplates(prev => prev.filter(t => t.id !== template.id))
    } catch (error) {
      console.error('Ошибка удаления шаблона:', error)
      alert('Ошибка при удалении шаблона')
    }
  }

  const handleFork = async (template: ClusterTemplate) => {
    const newName = prompt(`Новое название для копии "${template.name}":`)
    if (!newName) return

    try {
      const forkedTemplate = await apiService.createTemplate({
        name: newName,
        description: `Копия шаблона "${template.name}"`,
        upper_graph: {
          topic: template.topic,
          locale: template.locale,
          intents_applied: template.intents_applied,
          clusters: template.clusters
        }
      })
      
      setTemplates(prev => [forkedTemplate, ...prev])
      alert(`Шаблон "${newName}" создан!`)
    } catch (error) {
      console.error('Ошибка создания копии:', error)
      alert('Ошибка при создании копии шаблона')
    }
  }

  const handlePreview = async (template: ClusterTemplate) => {
    try {
      const upperGraph = await apiService.getTemplateAsUpperGraph(template.id)
      setShowPreview(template)
    } catch (error) {
      console.error('Ошибка загрузки превью:', error)
      alert('Ошибка при загрузке превью шаблона')
    }
  }

  const handleLoad = async (template: ClusterTemplate) => {
    try {
      const upperGraph = await apiService.getTemplateAsUpperGraph(template.id)
      onTemplateLoad(upperGraph)
      onClose()
    } catch (error) {
      console.error('Ошибка загрузки шаблона:', error)
      alert('Ошибка при загрузке шаблона')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl border border-slate-200 max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Tag className="h-5 w-5" />
              Управление шаблонами
            </h3>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Filters */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  placeholder="Поиск по названию, теме или описанию..."
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <select
                value={filters.sortBy}
                onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value as any }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="date">По дате</option>
                <option value="name">По названию</option>
                <option value="clusters">По количеству кластеров</option>
              </select>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter size={16} className="text-gray-500" />
                <span className="text-sm text-gray-600">Теги:</span>
                {allTags.slice(0, 5).map(tag => (
                  <button
                    key={tag}
                    onClick={() => {
                      setFilters(prev => ({
                        ...prev,
                        tags: prev.tags.includes(tag)
                          ? prev.tags.filter(t => t !== tag)
                          : [...prev.tags, tag]
                      }))
                    }}
                    className={`px-2 py-1 text-xs rounded-full transition-colors ${
                      filters.tags.includes(tag)
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
                {allTags.length > 5 && (
                  <span className="text-xs text-gray-400">+{allTags.length - 5}</span>
                )}
              </div>

              <select
                value={filters.dateRange}
                onChange={(e) => setFilters(prev => ({ ...prev, dateRange: e.target.value as any }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">Все время</option>
                <option value="week">За неделю</option>
                <option value="month">За месяц</option>
                <option value="year">За год</option>
              </select>
            </div>
          </div>

          {/* Templates Grid */}
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Загрузка шаблонов...</p>
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Tag className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium">Шаблоны не найдены</p>
              <p className="text-sm">Попробуйте изменить фильтры или создать новый шаблон</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTemplates.map(template => (
                <div
                  key={template.id}
                  className="border border-slate-200 rounded-lg p-4 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 mb-1">{template.name}</h4>
                      <p className="text-sm text-gray-600 mb-2">{template.topic}</p>
                      <p className="text-xs text-gray-500 line-clamp-2">{template.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                    <div className="flex items-center gap-1">
                      <Hash size={12} />
                      {template.cluster_count} кластеров
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar size={12} />
                      {new Date(template.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  {template.tags && template.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {template.tags.slice(0, 3).map(tag => (
                        <span
                          key={tag}
                          className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded"
                        >
                          {tag}
                        </span>
                      ))}
                      {template.tags.length > 3 && (
                        <span className="text-xs text-gray-400">+{template.tags.length - 3}</span>
                      )}
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleLoad(template)}
                      className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                    >
                      Загрузить
                    </button>
                    
                    <div className="flex gap-1">
                      <button
                        onClick={() => handlePreview(template)}
                        className="p-2 text-slate-400 hover:text-slate-700 transition-colors"
                        title="Превью"
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        onClick={() => setShowEditDialog(template)}
                        className="p-2 text-slate-400 hover:text-slate-700 transition-colors"
                        title="Редактировать"
                      >
                        <Edit3 size={14} />
                      </button>
                      <button
                        onClick={() => handleFork(template)}
                        className="p-2 text-slate-400 hover:text-slate-700 transition-colors"
                        title="Создать копию"
                      >
                        <Copy size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(template)}
                        className="p-2 text-red-400 hover:text-red-600 transition-colors"
                        title="Удалить"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Показано {filteredTemplates.length} из {templates.length} шаблонов
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-700 border border-slate-300 rounded-md hover:bg-slate-100 transition-colors"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-60">
          <div className="bg-white rounded-xl border border-slate-200 max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Превью шаблона: {showPreview.name}</h3>
                <button
                  onClick={() => setShowPreview(null)}
                  className="text-slate-400 hover:text-slate-700"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Информация</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div><strong>Тема:</strong> {showPreview.topic}</div>
                    <div><strong>Кластеров:</strong> {showPreview.cluster_count}</div>
                    <div><strong>Интенты:</strong> {showPreview.intents_applied.join(', ')}</div>
                    <div><strong>Создан:</strong> {new Date(showPreview.created_at).toLocaleString()}</div>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Кластеры</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {showPreview.clusters.map((cluster, index) => (
                      <div key={cluster.cluster_id} className="p-3 bg-slate-50 rounded border border-slate-200 text-sm">
                        <div className="font-medium">{cluster.name}</div>
                        <div className="text-gray-600">
                          {cluster.gpt_intent} • {cluster.demand_level} • {cluster.parent_theme}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-slate-200 bg-slate-50">
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowPreview(null)}
                  className="px-4 py-2 text-slate-700 border border-slate-300 rounded-md hover:bg-slate-100 transition-colors"
                >
                  Закрыть
                </button>
                <button
                  onClick={() => {
                    handleLoad(showPreview)
                    setShowPreview(null)
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Загрузить шаблон
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
