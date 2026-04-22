import React, { useState } from 'react'
import { X, Upload, FileText } from 'lucide-react'
import * as XLSX from 'xlsx'

interface Props {
  isOpen: boolean
  onClose: () => void
  onUpload: (queries: string[], intents: string[]) => void
  selectedIntents: string[]
}

export default function BulkUploadModal({ isOpen, onClose, onUpload, selectedIntents }: Props) {
  const [textInput, setTextInput] = useState('')
  const [activeTab, setActiveTab] = useState<'text' | 'file'>('text')
  const [fileError, setFileError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleTextSubmit = () => {
    if (!textInput.trim()) {
      setFileError('Пожалуйста, введите хотя бы один запрос')
      return
    }

    const queries = textInput
      .split('\n')
      .map(q => q.trim())
      .filter(q => q.length > 0)

    if (queries.length === 0) {
      setFileError('Не найдено валидных запросов')
      return
    }

    if (selectedIntents.length === 0) {
      setFileError('Пожалуйста, выберите хотя бы один тип запроса')
      return
    }

    onUpload(queries, selectedIntents)
    handleClose()
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setLoading(true)
    setFileError('')

    try {
      const text = await file.text()
      let queries: string[] = []

      if (file.name.endsWith('.csv')) {
        queries = text
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0)
      } else if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
        const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' })
        const sheet = workbook.Sheets[workbook.SheetNames[0]]
        const data = XLSX.utils.sheet_to_json(sheet, { header: 1 })
        queries = data
          .map(row => (Array.isArray(row) ? row[0] : row))
          .filter(q => typeof q === 'string' && q.trim().length > 0)
          .map(q => (typeof q === 'string' ? q.trim() : String(q).trim()))
      } else {
        setFileError('Поддерживаются только CSV и XLSX файлы')
        return
      }

      if (queries.length === 0) {
        setFileError('Не найдено запросов в файле')
        return
      }

      if (selectedIntents.length === 0) {
        setFileError('Пожалуйста, выберите хотя бы один тип запроса')
        return
      }

      onUpload(queries, selectedIntents)
      handleClose()
    } catch (error) {
      setFileError(`Ошибка при чтении файла: ${error instanceof Error ? error.message : 'неизвестная ошибка'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setTextInput('')
    setFileError('')
    setActiveTab('text')
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">Массовая загрузка запросов</h2>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6">
          {/* Tabs */}
          <div className="flex gap-4 mb-6 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('text')}
              className={`pb-2 px-2 font-medium transition-colors ${
                activeTab === 'text'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <FileText size={16} className="inline mr-2" />
              Вставить текст
            </button>
            <button
              onClick={() => setActiveTab('file')}
              className={`pb-2 px-2 font-medium transition-colors ${
                activeTab === 'file'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Upload size={16} className="inline mr-2" />
              Загрузить файл
            </button>
          </div>

          {/* Text Tab */}
          {activeTab === 'text' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Введите запросы (по одному на строку):
              </label>
              <textarea
                value={textInput}
                onChange={e => setTextInput(e.target.value)}
                placeholder="купить товар&#10;как выбрать товар&#10;отзывы о товаре&#10;цена товара"
                className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              />
              <div className="mt-2 text-sm text-gray-600">
                Введено: {textInput.split('\n').filter(q => q.trim().length > 0).length} запросов
              </div>
            </div>
          )}

          {/* File Tab */}
          {activeTab === 'file' && (
            <div>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors">
                <Upload size={48} className="mx-auto text-gray-400 mb-3" />
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileUpload}
                    disabled={loading}
                    className="hidden"
                  />
                  <span className="text-blue-600 font-medium hover:text-blue-700">
                    Выберите файл
                  </span>
                </label>
                <p className="text-gray-600 text-sm mt-2">
                  или перетащите CSV/XLSX файл сюда
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  Запросы должны быть в первом столбце по одному на строку
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {fileError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {fileError}
            </div>
          )}

          {/* Selected Intents Info */}
          <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded">
            <p className="text-sm font-medium text-blue-900">
              Выбранные типы запросов:
            </p>
            <p className="text-sm text-blue-800 mt-1">
              {selectedIntents.length > 0
                ? selectedIntents.join(', ')
                : 'Пожалуйста, выберите типы на предыдущем шаге'}
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-3 mt-6 justify-end">
            <button
              onClick={handleClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors font-medium"
            >
              Отмена
            </button>
            <button
              onClick={handleTextSubmit}
              disabled={loading || !textInput.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
            >
              <Upload size={16} />
              {loading ? 'Загрузка...' : 'Загрузить запросы'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
