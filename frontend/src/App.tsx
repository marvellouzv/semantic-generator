import React, { useState, useEffect } from 'react'
import { History, Save } from 'lucide-react'
import SetupScreen from './components/SetupScreen'
import UpperReviewScreen from './components/UpperReviewScreen'
import LoadingOverlay from './components/LoadingOverlay'
import HistoryPanel from './components/HistoryPanel'
import TemplateManager from './components/TemplateManager'
import apiService from './api'
import { historyManager } from './utils/history'
import type { 
  UpperGraphRequest, 
  UpperGraph, 
  UpperCluster 
} from './types'
import './App.css'

type Screen = 'setup' | 'review'

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('setup')
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('Генерация...')
  const [error, setError] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [showTemplateManager, setShowTemplateManager] = useState(false)
  
  // State for the workflow
  const [setupData, setSetupData] = useState<UpperGraphRequest | null>(null)
  const [upperGraph, setUpperGraph] = useState<UpperGraph | null>(null)

  // Initialize history manager
  useEffect(() => {
    historyManager.init().catch(console.error)
  }, [])

  const StepHeader = () => (
    <div className="w-full sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center gap-2">
        {(['setup','review'] as Screen[]).map((s, idx) => (
          <button
            key={s}
            onClick={() => {
              // Переключение без потери состояния: показываем только доступные шаги
              if (s === 'review' && !upperGraph) return
              setCurrentScreen(s)
            }}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold tracking-wide uppercase border ${
              currentScreen === s
                ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
            }`}
          >
            {idx+1}. {s === 'setup' ? 'Этап 1: Настройка' : 'Этап 2: Кластеры'}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={() => setShowTemplateManager(true)}
            className="px-3 py-1.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-md hover:bg-blue-100 text-sm flex items-center gap-1"
            title="Управление шаблонами (Ctrl+T)"
          >
            <Save size={14} />
            Шаблоны
          </button>
          <button
            onClick={() => setShowHistory(true)}
            className="px-3 py-1.5 bg-slate-100 text-slate-700 border border-slate-200 rounded-md hover:bg-slate-200 text-sm flex items-center gap-1"
            title="История генераций (Ctrl+H)"
          >
            <History size={14} />
            История
          </button>
          <div className="text-xs text-gray-500">
            {setupData?.template_id ? 'Режим: Дополнение шаблона' : 'Режим: Новая генерация'}
          </div>
        </div>
      </div>
    </div>
  )

  const handleSetupSubmit = async (data: UpperGraphRequest) => {
    setLoading(true)
    setError(null)
    setSetupData(data)
    
    // Устанавливаем сообщение в зависимости от режима
    if (data.template_id) {
      setLoadingMessage('Дополняем шаблон новыми кластерами через GPT-5...')
    } else {
      setLoadingMessage('Генерируем кластеры с максимальным покрытием через GPT-5...')
    }
    
    try {
      console.log('[UI] → POST /api/v1/upper-graph', data)
      const startTime = Date.now()
      const result = await apiService.generateUpperGraph(data)
      const generationTime = Date.now() - startTime
      console.log('[UI] ← /api/v1/upper-graph OK')
      
      // Сохраняем в историю
      try {
        await historyManager.saveGeneration(
          result,
          data.topic,
          data.intents,
          data.locale,
          generationTime
        )
      } catch (historyError) {
        console.warn('Failed to save to history:', historyError)
      }
      
      setUpperGraph(result)
      setCurrentScreen('review')
    } catch (err: any) {
      // Обработка детальных ошибок от backend
      let errorMessage = 'Ошибка генерации кластеров'
      
      if (err?.response?.data?.detail) {
        const detail = err.response.data.detail
        if (typeof detail === 'string') {
          errorMessage = detail
        } else if (detail.message) {
          errorMessage = `${detail.message} (${detail.error_type || 'Unknown error'})`
        }
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
      console.error('Upper graph generation failed:', err)
      console.error('Error details:', err?.response?.data)
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateLoad = (templateUpperGraph: UpperGraph) => {
    setUpperGraph(templateUpperGraph)
    setCurrentScreen('review')
  }

  const handleRestoreGeneration = (upperGraph: UpperGraph) => {
    setUpperGraph(upperGraph)
    setCurrentScreen('review')
  }


  const handleClustersUpdate = (clusters: UpperCluster[]) => {
    if (upperGraph) {
      setUpperGraph({
        ...upperGraph,
        clusters
      })
    }
  }


  const handleBackToSetup = () => {
    setCurrentScreen('setup')
    setUpperGraph(null)
    setError(null)
  }

  // Error display component
  const ErrorDisplay = ({ message }: { message: string }) => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Ошибка</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{message}</p>
            </div>
            <div className="mt-4">
              <button
                onClick={() => setError(null)}
                className="bg-red-100 px-3 py-2 rounded-md text-sm font-medium text-red-800 hover:bg-red-200"
              >
                Закрыть
              </button>
              <button
                onClick={handleBackToSetup}
                className="ml-3 bg-red-100 px-3 py-2 rounded-md text-sm font-medium text-red-800 hover:bg-red-200"
              >
                Начать заново
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )


  return (
    <div className="app-shell">
      <StepHeader />
      {renderCurrentScreen()}
      <LoadingOverlay 
        isVisible={loading} 
        message={loadingMessage}
        estimatedTime={300}
        onCancel={() => setLoading(false)}
      />
      {showHistory && (
        <HistoryPanel
          onRestoreGeneration={handleRestoreGeneration}
          onClose={() => setShowHistory(false)}
        />
      )}

      {showTemplateManager && (
        <TemplateManager
          onTemplateLoad={(template) => {
            // Загружаем шаблон как UpperGraph
            handleTemplateLoad(template as any)
            setShowTemplateManager(false)
          }}
          onTemplateEdit={(template) => {
            // Для редактирования пока просто загружаем
            handleTemplateLoad(template as any)
            setShowTemplateManager(false)
          }}
          onClose={() => setShowTemplateManager(false)}
          showTemplateManager={true}
        />
      )}
    </div>
  )

  function renderCurrentScreen() {
    if (error) {
      return <ErrorDisplay message={error} />
    }

    switch (currentScreen) {
      case 'setup':
        return <SetupScreen onSubmit={handleSetupSubmit} onTemplateLoad={handleTemplateLoad} loading={loading} />
      
      case 'review':
        if (!upperGraph) {
          return <ErrorDisplay message="Данные кластеров не найдены" />
        }
        return (
          <UpperReviewScreen
            upperGraph={upperGraph}
            onClustersUpdate={handleClustersUpdate}
            onProceed={() => {}} // Убрали третий этап
            loading={loading}
          />
        )
      
      default:
        return <ErrorDisplay message="Неизвестное состояние приложения" />
    }
  }
}
