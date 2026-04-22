import React, { useState, useMemo } from 'react'
import { Download, FileText, FileSpreadsheet, Database, X, Check, Settings } from 'lucide-react'
import type { UpperCluster, UpperGraph } from '../types'
import apiService from '../api'

interface Props {
  clusters: UpperCluster[]
  upperGraph: UpperGraph
  filteredClusters?: UpperCluster[]
  onClose: () => void
}

interface ExportField {
  key: string
  label: string
  enabled: boolean
  required: boolean
}

interface ExportTemplate {
  id: string
  name: string
  fields: string[]
}

const AVAILABLE_FIELDS: ExportField[] = [
  { key: 'cluster_id', label: 'ID кластера', enabled: true, required: true },
  { key: 'name', label: 'Название', enabled: true, required: true },
  { key: 'gpt_intent', label: 'Интент', enabled: true, required: false },
  { key: 'demand_level', label: 'Уровень спроса', enabled: true, required: false },
  { key: 'parent_category', label: 'Родительская категория', enabled: true, required: false },
  { key: 'parent_theme', label: 'Родительская тема', enabled: true, required: false },
  { key: 'intent_mix', label: 'Смесь интентов', enabled: false, required: false },
  { key: 'seed_examples', label: 'Примеры запросов', enabled: false, required: false },
  { key: 'tags', label: 'Теги', enabled: false, required: false },
  { key: 'notes', label: 'Заметки', enabled: false, required: false }
]

const EXPORT_FORMATS = [
  { id: 'xlsx', label: 'Excel (XLSX)', icon: FileSpreadsheet, description: 'Лучший для анализа данных' },
  { id: 'csv', label: 'CSV', icon: FileText, description: 'Универсальный формат' },
  { id: 'json', label: 'JSON', icon: Database, description: 'Для разработчиков' }
]

const SAVED_TEMPLATES: ExportTemplate[] = [
  { id: 'basic', name: 'Базовый', fields: ['cluster_id', 'name', 'gpt_intent', 'demand_level'] },
  { id: 'detailed', name: 'Детальный', fields: ['cluster_id', 'name', 'gpt_intent', 'parent_category', 'demand_level', 'parent_theme', 'tags'] },
  { id: 'full', name: 'Полный', fields: ['cluster_id', 'name', 'gpt_intent', 'parent_category', 'demand_level', 'parent_theme', 'intent_mix', 'seed_examples', 'tags', 'notes'] }
]

export default function ExportDialog({ clusters, upperGraph, filteredClusters, onClose }: Props) {
  const [selectedFormat, setSelectedFormat] = useState('xlsx')
  const [selectedFields, setSelectedFields] = useState<ExportField[]>(() => 
    AVAILABLE_FIELDS.map(field => ({ ...field, enabled: field.required }))
  )
  const [exportScope, setExportScope] = useState<'all' | 'filtered' | 'selected'>('all')
  const [includeMetadata, setIncludeMetadata] = useState(true)
  const [customFilename, setCustomFilename] = useState('')
  const [isExporting, setIsExporting] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const exportData = useMemo(() => {
    let dataToExport = clusters
    
    if (exportScope === 'filtered' && filteredClusters) {
      dataToExport = filteredClusters
    }
    
    return dataToExport
  }, [clusters, filteredClusters, exportScope])

  const enabledFields = selectedFields.filter(f => f.enabled)
  const requiredFields = selectedFields.filter(f => f.required && !f.enabled)

  const handleFieldToggle = (fieldKey: string) => {
    setSelectedFields(prev => 
      prev.map(field => 
        field.key === fieldKey 
          ? { ...field, enabled: !field.enabled }
          : field
      )
    )
  }

  const handleTemplateSelect = (template: ExportTemplate) => {
    setSelectedFields(prev => 
      prev.map(field => ({
        ...field,
        enabled: template.fields.includes(field.key)
      }))
    )
  }

  const handleExport = async () => {
    if (requiredFields.length > 0) {
      alert('Пожалуйста, включите все обязательные поля')
      return
    }

    setIsExporting(true)
    try {
      // Prepare data with selected fields
      const exportRows = exportData.map(cluster => {
        const row: Record<string, any> = {}
        
        enabledFields.forEach(field => {
          const value = cluster[field.key as keyof UpperCluster]
          
          if (field.key === 'intent_mix' && Array.isArray(value)) {
            row[field.label] = value.join(', ')
          } else if (field.key === 'seed_examples' && Array.isArray(value)) {
            row[field.label] = value.join(' | ')
          } else if (field.key === 'tags' && Array.isArray(value)) {
            row[field.label] = value.join(', ')
          } else {
            row[field.label] = value || ''
          }
        })
        
        return row
      })

      // Add metadata if requested
      if (includeMetadata) {
        const metadata = {
          'Экспорт создан': new Date().toLocaleString('ru-RU'),
          'Тема': upperGraph.topic,
          'Локаль': upperGraph.locale,
          'Интенты': upperGraph.intents_applied.join(', '),
          'Всего кластеров': exportData.length,
          'Поля экспорта': enabledFields.map(f => f.label).join(', ')
        }
        
        // Add metadata as first row for some formats
        if (selectedFormat === 'xlsx') {
          exportRows.unshift(metadata)
        }
      }

      if (selectedFormat === 'json') {
        // Export as JSON
        const jsonData = {
          metadata: includeMetadata ? {
            exportDate: new Date().toISOString(),
            topic: upperGraph.topic,
            locale: upperGraph.locale,
            intents: upperGraph.intents_applied,
            totalClusters: exportData.length,
            fields: enabledFields.map(f => f.key)
          } : undefined,
          clusters: exportRows
        }
        
        const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = customFilename || `clusters_${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        // Use existing API for XLSX/CSV
        const blob = await apiService.exportClusters({
          format: selectedFormat as 'xlsx' | 'csv',
          clusters: exportData
        })
        
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = customFilename || `clusters_${new Date().toISOString().split('T')[0]}.${selectedFormat}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }

      onClose()
    } catch (error) {
      console.error('Export failed:', error)
      alert('Ошибка экспорта. Попробуйте еще раз.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl border border-slate-200 max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Download className="h-5 w-5" />
              Экспорт кластеров
            </h3>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="space-y-6">
            {/* Export Scope */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-3">
                Область экспорта
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="all"
                    checked={exportScope === 'all'}
                    onChange={(e) => setExportScope(e.target.value as any)}
                    className="mr-2"
                  />
                  <span className="text-sm">Все кластеры ({clusters.length})</span>
                </label>
                {filteredClusters && (
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="filtered"
                      checked={exportScope === 'filtered'}
                      onChange={(e) => setExportScope(e.target.value as any)}
                      className="mr-2"
                    />
                    <span className="text-sm">Отфильтрованные кластеры ({filteredClusters.length})</span>
                  </label>
                )}
              </div>
            </div>

            {/* Format Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-3">
                Формат файла
              </label>
              <div className="grid grid-cols-1 gap-3">
                {EXPORT_FORMATS.map(format => {
                  const Icon = format.icon
                  return (
                    <label
                      key={format.id}
                      className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedFormat === format.id
                          ? 'border-blue-500 bg-blue-50 shadow-sm'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <input
                        type="radio"
                        value={format.id}
                        checked={selectedFormat === format.id}
                        onChange={(e) => setSelectedFormat(e.target.value)}
                        className="sr-only"
                      />
                      <Icon className="h-5 w-5 text-slate-600 mr-3" />
                      <div>
                        <div className="font-medium">{format.label}</div>
                        <div className="text-sm text-slate-500">{format.description}</div>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            {/* Field Selection */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-slate-700">
                  Поля для экспорта
                </label>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                >
                  <Settings size={14} />
                  {showAdvanced ? 'Скрыть' : 'Настройки'}
                </button>
              </div>

              {/* Quick Templates */}
              <div className="mb-4 flex gap-2">
                {SAVED_TEMPLATES.map(template => (
                  <button
                    key={template.id}
                    onClick={() => handleTemplateSelect(template)}
                    className="px-3 py-1 text-xs bg-slate-100 text-slate-700 rounded-full hover:bg-slate-200 transition-colors"
                  >
                    {template.name}
                  </button>
                ))}
              </div>

              <div className="space-y-2 max-h-40 overflow-y-auto">
                {selectedFields.map(field => (
                  <label key={field.key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={field.enabled}
                      onChange={() => handleFieldToggle(field.key)}
                      disabled={field.required}
                      className="mr-2"
                    />
                    <span className={`text-sm ${field.required ? 'text-slate-500' : 'text-slate-700'}`}>
                      {field.label}
                      {field.required && <span className="text-red-500 ml-1">*</span>}
                    </span>
                  </label>
                ))}
              </div>

              {requiredFields.length > 0 && (
                <div className="mt-2 text-sm text-red-600">
                  Включите обязательные поля: {requiredFields.map(f => f.label).join(', ')}
                </div>
              )}
            </div>

            {/* Advanced Options */}
            {showAdvanced && (
              <div className="space-y-4 pt-4 border-t border-slate-200">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeMetadata}
                      onChange={(e) => setIncludeMetadata(e.target.checked)}
                      className="mr-2"
                    />
                    <span className="text-sm text-slate-700">Включить метаданные</span>
                  </label>
                  <div className="text-xs text-slate-500 mt-1">
                    Добавит информацию о теме, интентах и дате экспорта
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Имя файла (необязательно)
                  </label>
                  <input
                    type="text"
                    value={customFilename}
                    onChange={(e) => setCustomFilename(e.target.value)}
                    placeholder={`clusters_${new Date().toISOString().split('T')[0]}.${selectedFormat}`}
                    className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-6 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-600">
              Будет экспортировано: {exportData.length} кластеров, {enabledFields.length} полей
            </div>
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-slate-700 border border-slate-300 rounded-md hover:bg-slate-100 transition-colors"
              >
                Отмена
              </button>
              <button
                onClick={handleExport}
                disabled={isExporting || requiredFields.length > 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isExporting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Экспорт...
                  </>
                ) : (
                  <>
                    <Download size={16} />
                    Экспортировать
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


