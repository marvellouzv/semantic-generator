import React, { useState, useEffect } from 'react'
import { Upload, Download, AlertCircle, CheckCircle, Clock, X } from 'lucide-react'
import apiService from '../api'

interface BatchStatus {
  batch_id: string
  filename: string
  total: number
  completed: number
  failed: number
  pending: number
  progress: string
  status: 'processing' | 'completed'
}

interface BatchResult {
  batch_id: string
  filename: string
  results: Array<{
    topic: string
    status: 'success' | 'error'
    cluster_count: number
    error?: string
  }>
  summary: {
    total: number
    successful: number
    failed: number
    total_clusters: number
  }
}

interface Props {
  onClose?: () => void
  isVisible?: boolean
}

export default function BatchProcessing({ onClose, isVisible = true }: Props) {
  const [batchId, setBatchId] = useState<string | null>(null)
  const [status, setStatus] = useState<BatchStatus | null>(null)
  const [results, setResults] = useState<BatchResult | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Poll for status updates
  useEffect(() => {
    if (!batchId || !status || status.status === 'completed') return

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/batch/jobs/${batchId}`)
        const newStatus = await res.json()
        setStatus(newStatus)

        // When completed, fetch results
        if (newStatus.status === 'completed') {
          const resultsRes = await fetch(`/api/v1/batch/jobs/${batchId}/results`)
          const resultsData = await resultsRes.json()
          setResults(resultsData)
        }
      } catch (err) {
        console.error('Error fetching batch status:', err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [batchId, status])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0])
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/v1/batch/upload', {
        method: 'POST',
        body: formData
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const data = await res.json()
      setBatchId(data.batch_id)
      setStatus({
        batch_id: data.batch_id,
        filename: file.name,
        total: data.total_topics,
        completed: 0,
        failed: 0,
        pending: data.total_topics,
        progress: '0%',
        status: 'processing'
      })
    } catch (err: any) {
      setError(err.message || 'Error uploading file')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format: 'xlsx' | 'csv' | 'json') => {
    if (!batchId) return

    try {
      const res = await fetch(`/api/v1/batch/jobs/${batchId}/export?format=${format}`, {
        method: 'POST'
      })

      if (!res.ok) throw new Error('Export failed')

      const data = await res.json()
      const filename = data.filename
      
      if (format === 'xlsx' && data.binary) {
        // Decode hex data for binary export
        const binaryString = atob(data.data.match(/.{1,2}/g)!.map(x => String.fromCharCode(parseInt(x, 16))).join(''))
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }
        const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        a.click()
      } else {
        // Text-based export
        const blob = new Blob([data.data], {
          type: format === 'json' ? 'application/json' : 'text/csv'
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        a.click()
      }
    } catch (err: any) {
      setError(err.message || 'Export failed')
    }
  }

  const reset = () => {
    setBatchId(null)
    setStatus(null)
    setResults(null)
    setFile(null)
    setError(null)
  }

  if (!isVisible) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-xl font-semibold">📁 Массовая обработка</h2>
          {onClose && (
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              <X size={24} />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">📋 Инструкция:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Подготовьте CSV или XLSX файл с колонками: <code className="bg-blue-100 px-2 py-1 rounded">topic</code>, <code className="bg-blue-100 px-2 py-1 rounded">intents</code></li>
              <li>• <code className="bg-blue-100 px-2 py-1 rounded">topic</code> - тема для генерации</li>
              <li>• <code className="bg-blue-100 px-2 py-1 rounded">intents</code> - интенты через запятую (commercial, informational, service и т.д.)</li>
              <li>• Если &gt;= 20 тем - будет использована асинхронная обработка</li>
            </ul>
          </div>

          {/* Upload Section */}
          {!batchId && (
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition">
                <Upload className="mx-auto mb-3 text-gray-400" size={40} />
                <input
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleFileChange}
                  className="hidden"
                  id="batch-file"
                  disabled={loading}
                />
                <label htmlFor="batch-file" className="block cursor-pointer">
                  <p className="text-lg font-medium text-gray-700">Выберите файл</p>
                  <p className="text-sm text-gray-500 mt-1">CSV или XLSX формат</p>
                  {file && <p className="text-sm text-green-600 mt-2">✓ {file.name}</p>}
                </label>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-3">
                  <AlertCircle className="text-red-600 mt-0.5 flex-shrink-0" size={20} />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={!file || loading}
                className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {loading ? 'Загрузка...' : 'Начать обработку'}
              </button>
            </div>
          )}

          {/* Progress Section */}
          {status && !results && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Прогресс</span>
                  <span className="text-sm font-bold text-blue-600">{status.progress}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                    style={{ width: status.progress }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-4 gap-2">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">Всего</p>
                  <p className="text-lg font-bold text-gray-900">{status.total}</p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">Завершено</p>
                  <p className="text-lg font-bold text-green-600">{status.completed}</p>
                </div>
                <div className="bg-yellow-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">В очереди</p>
                  <p className="text-lg font-bold text-yellow-600">{status.pending}</p>
                </div>
                <div className="bg-red-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">Ошибок</p>
                  <p className="text-lg font-bold text-red-600">{status.failed}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Clock size={16} />
                Обработка в фоне, пожалуйста подождите...
              </div>
            </div>
          )}

          {/* Results Section */}
          {results && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-green-600" size={24} />
                <span className="text-lg font-semibold text-gray-900">Обработка завершена!</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-600">Успешно обработано</p>
                  <p className="text-2xl font-bold text-green-600">{results.summary.successful}/{results.summary.total}</p>
                </div>
                <div className="bg-blue-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-600">Всего кластеров</p>
                  <p className="text-2xl font-bold text-blue-600">{results.summary.total_clusters}</p>
                </div>
              </div>

              {results.summary.failed > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    ⚠️ {results.summary.failed} тем не удалось обработать
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => handleExport('xlsx')}
                  className="flex-1 px-3 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800 flex items-center justify-center gap-2 transition"
                >
                  <Download size={16} />
                  Excel
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2 transition"
                >
                  <Download size={16} />
                  CSV
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className="flex-1 px-3 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 flex items-center justify-center gap-2 transition"
                >
                  <Download size={16} />
                  JSON
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-4 flex justify-between items-center">
          {batchId && (
            <p className="text-xs text-gray-500">ID: {batchId.substring(0, 12)}...</p>
          )}
          <div className="flex gap-2 ml-auto">
            {batchId && (
              <button
                onClick={reset}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
              >
                Новая обработка
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Закрыть
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
