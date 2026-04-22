import React, { useState, useEffect } from 'react'
import { History, Clock, BarChart3, Download, Upload, Trash2, RotateCcw, GitCompare, X } from 'lucide-react'
import type { GenerationHistory, HistoryComparison } from '../utils/history'
import { historyManager } from '../utils/history'

interface Props {
  onRestoreGeneration: (upperGraph: any) => void
  onClose: () => void
}

export default function HistoryPanel({ onRestoreGeneration, onClose }: Props) {
  const [generations, setGenerations] = useState<GenerationHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedGenerations, setSelectedGenerations] = useState<string[]>([])
  const [comparison, setComparison] = useState<HistoryComparison | null>(null)
  const [showComparison, setShowComparison] = useState(false)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      setLoading(true)
      const history = await historyManager.getAllGenerations()
      setGenerations(history)
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRestore = async (id: string) => {
    try {
      const upperGraph = await historyManager.restoreGeneration(id)
      if (upperGraph) {
        onRestoreGeneration(upperGraph)
        onClose()
      }
    } catch (error) {
      console.error('Failed to restore generation:', error)
      alert('Ошибка при восстановлении генерации')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Удалить эту генерацию из истории?')) return
    
    try {
      await historyManager.deleteGeneration(id)
      await loadHistory()
    } catch (error) {
      console.error('Failed to delete generation:', error)
      alert('Ошибка при удалении генерации')
    }
  }

  const handleCompare = async () => {
    if (selectedGenerations.length !== 2) {
      alert('Выберите ровно 2 генерации для сравнения')
      return
    }

    try {
      const comparison = await historyManager.compareGenerations(
        selectedGenerations[0],
        selectedGenerations[1]
      )
      if (comparison) {
        setComparison(comparison)
        setShowComparison(true)
      }
    } catch (error) {
      console.error('Failed to compare generations:', error)
      alert('Ошибка при сравнении генераций')
    }
  }

  const handleExport = async () => {
    try {
      const blob = await historyManager.exportHistory()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `semantic-generator-history-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export history:', error)
      alert('Ошибка при экспорте истории')
    }
  }

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const importedCount = await historyManager.importHistory(file)
      await loadHistory()
      alert(`Импортировано ${importedCount} генераций`)
    } catch (error) {
      console.error('Failed to import history:', error)
      alert('Ошибка при импорте истории')
    }
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('ru-RU')
  }

  const formatDuration = (ms: number) => {
    const seconds = Math.round(ms / 1000)
    if (seconds < 60) return `${seconds}с`
    const minutes = Math.round(seconds / 60)
    return `${minutes}м`
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span>Загрузка истории...</span>
          </div>
        </div>
      </div>
    )
  }

  if (showComparison && comparison) {
    return (
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl border border-slate-200 w-full max-w-6xl max-h-[90vh] overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b">
            <h2 className="text-xl font-semibold">Сравнение генераций</h2>
            <button
              onClick={() => setShowComparison(false)}
              className="text-slate-500 hover:text-slate-700"
            >
              <X size={20} />
            </button>
          </div>
          
          <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Добавленные кластеры */}
              {comparison.differences.addedClusters.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-green-800 mb-3">
                    Добавлено кластеров: {comparison.differences.addedClusters.length}
                  </h3>
                  <div className="space-y-2">
                    {comparison.differences.addedClusters.map((cluster, index) => (
                      <div key={index} className="bg-white p-2 rounded border">
                        <div className="font-medium">{cluster.name}</div>
                        <div className="text-sm text-gray-600">
                          {cluster.gpt_intent} • {cluster.demand_level}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Удаленные кластеры */}
              {comparison.differences.removedClusters.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-red-800 mb-3">
                    Удалено кластеров: {comparison.differences.removedClusters.length}
                  </h3>
                  <div className="space-y-2">
                    {comparison.differences.removedClusters.map((cluster, index) => (
                      <div key={index} className="bg-white p-2 rounded border">
                        <div className="font-medium">{cluster.name}</div>
                        <div className="text-sm text-gray-600">
                          {cluster.gpt_intent} • {cluster.demand_level}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Измененные кластеры */}
              {comparison.differences.modifiedClusters.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 md:col-span-2">
                  <h3 className="text-lg font-medium text-yellow-800 mb-3">
                    Изменено кластеров: {comparison.differences.modifiedClusters.length}
                  </h3>
                  <div className="space-y-3">
                    {comparison.differences.modifiedClusters.map((item, index) => (
                      <div key={index} className="bg-white p-3 rounded border">
                        <div className="font-medium mb-2">{item.cluster.name}</div>
                        <div className="space-y-1">
                          {Object.entries(item.changes).map(([field, change]) => (
                            <div key={field} className="text-sm">
                              <span className="font-medium">{field}:</span>
                              <span className="text-red-600 line-through ml-2">{String(change.old)}</span>
                              <span className="text-green-600 ml-2">{String(change.new)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Изменения метаданных */}
              {Object.keys(comparison.differences.metadataChanges).length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 md:col-span-2">
                  <h3 className="text-lg font-medium text-blue-800 mb-3">
                    Изменения метаданных
                  </h3>
                  <div className="space-y-1">
                    {Object.entries(comparison.differences.metadataChanges).map(([field, change]) => (
                      <div key={field} className="text-sm">
                        <span className="font-medium">{field}:</span>
                        <span className="text-red-600 line-through ml-2">{String(change.old)}</span>
                        <span className="text-green-600 ml-2">{String(change.new)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl border border-slate-200 w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-semibold">История генераций</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              className="px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 flex items-center gap-1"
            >
              <Download size={14} />
              Экспорт
            </button>
            <label className="px-3 py-1 bg-slate-100 text-slate-700 border border-slate-200 rounded hover:bg-slate-200 cursor-pointer flex items-center gap-1">
              <Upload size={14} />
              Импорт
              <input
                type="file"
                accept=".json"
                onChange={handleImport}
                className="hidden"
              />
            </label>
            <button
              onClick={onClose}
              className="text-slate-500 hover:text-slate-700"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
          {generations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <History size={48} className="mx-auto mb-4 text-gray-300" />
              <p className="text-lg mb-2">История пуста</p>
              <p className="text-sm">Сгенерируйте кластеры, чтобы они появились в истории</p>
            </div>
          ) : (
            <div className="space-y-3">
              {generations.map((generation) => (
                <div
                  key={generation.id}
                  className={`border rounded-lg p-4 transition-all ${
                    generation.isActive
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900">
                          {generation.topic}
                        </h3>
                        {generation.isActive && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                            Активная
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <Clock size={14} />
                          {formatDate(generation.timestamp)}
                        </span>
                        <span className="flex items-center gap-1">
                          <BarChart3 size={14} />
                          {generation.metadata.clusterCount} кластеров
                        </span>
                        <span>Время: {formatDuration(generation.metadata.generationTime)}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedGenerations.includes(generation.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedGenerations(prev => [...prev, generation.id])
                          } else {
                            setSelectedGenerations(prev => prev.filter(id => id !== generation.id))
                          }
                        }}
                        className="rounded border-gray-300"
                      />
                      <button
                        onClick={() => handleRestore(generation.id)}
                        className="p-1 text-blue-600 hover:text-blue-800"
                        title="Восстановить"
                      >
                        <RotateCcw size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(generation.id)}
                        className="p-1 text-red-600 hover:text-red-800"
                        title="Удалить"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-600">
                    <div>Интенты: {generation.intents.join(', ')}</div>
                    <div>Высокий спрос: {generation.metadata.highDemandCount}</div>
                    <div>Коммерческие: {generation.metadata.commercialCount}</div>
                    <div>Темы: {generation.metadata.parentThemes.length}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {generations.length > 0 && (
          <div className="p-4 border-t bg-slate-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Выбрано: {selectedGenerations.length} из {generations.length}
              </div>
              <div className="flex items-center gap-2">
                {selectedGenerations.length === 2 && (
                  <button
                    onClick={handleCompare}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
                  >
                    <GitCompare size={16} />
                    Сравнить
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
