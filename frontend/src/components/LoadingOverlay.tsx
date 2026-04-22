import React, { useState, useEffect } from 'react'
import { X, Clock, CheckCircle, AlertCircle, Brain, Zap, Target, Search, Loader } from 'lucide-react'

interface LoadingStep {
  id: string
  title: string
  description: string
  status: 'pending' | 'active' | 'completed' | 'error'
  duration?: number
  icon: React.ReactNode
}

interface LoadingOverlayProps {
  isVisible: boolean
  message?: string
  onCancel?: () => void
  estimatedTime?: number
  currentStep?: string
}

export default function LoadingOverlay({ 
  isVisible, 
  message = "Генерация...", 
  onCancel,
  estimatedTime = 300,
  currentStep
}: LoadingOverlayProps) {
  const [progress, setProgress] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [steps, setSteps] = useState<LoadingStep[]>([
    {
      id: 'analyze',
      title: 'Анализ тематики',
      description: 'GPT-5 анализирует введенную тематику и определяет оптимальную стратегию генерации',
      status: 'pending',
      icon: <Brain size={16} />
    },
    {
      id: 'reasoning',
      title: 'Reasoning процесс',
      description: 'GPT-5 использует цепочку рассуждений для создания качественных кластеров',
      status: 'pending',
      icon: <Zap size={16} />
    },
    {
      id: 'generate',
      title: 'Генерация кластеров',
      description: 'Создание семантических кластеров с учетом выбранных интентов',
      status: 'pending',
      icon: <Target size={16} />
    },
    {
      id: 'postprocess',
      title: 'Постобработка',
      description: 'Нормализация, дедупликация и оценка качества кластеров',
      status: 'pending',
      icon: <Search size={16} />
    }
  ])

  useEffect(() => {
    if (!isVisible) {
      setProgress(0)
      setElapsedTime(0)
      setSteps(prev => prev.map(step => ({ ...step, status: 'pending' })))
      return
    }

    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1)
      
      // Обновляем прогресс
      const timeProgress = Math.min((elapsedTime / estimatedTime) * 100, 95)
      setProgress(timeProgress)
      
      // Обновляем статусы шагов
      setSteps(prev => {
        const newSteps = [...prev]
        const stepDuration = estimatedTime / 4
        
        newSteps.forEach((step, index) => {
          const stepStartTime = index * stepDuration
          const stepEndTime = (index + 1) * stepDuration
          
          if (elapsedTime >= stepEndTime) {
            step.status = 'completed'
          } else if (elapsedTime >= stepStartTime) {
            step.status = 'active'
          }
        })
        
        return newSteps
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [isVisible, elapsedTime, estimatedTime])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getStepIcon = (step: LoadingStep) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />
      case 'active':
        return <Loader size={16} className="text-blue-500 animate-spin" />
      case 'error':
        return <AlertCircle size={16} className="text-red-500" />
      default:
        return step.icon
    }
  }

  const getStepColor = (step: LoadingStep) => {
    switch (step.status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'active':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  if (!isVisible) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl mx-4 w-full shadow-2xl">
        {/* Заголовок */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-12 h-12 border-4 border-blue-200 rounded-full animate-spin"></div>
              <div className="absolute top-0 left-0 w-12 h-12 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-800">
                🤖 GPT-5 работает
              </h3>
              <p className="text-sm text-gray-600">{message}</p>
            </div>
          </div>
          
          {onCancel && (
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Прогресс бар */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Прогресс</span>
            <span className="text-sm text-gray-500">
              {formatTime(elapsedTime)} / ~{formatTime(estimatedTime)}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {Math.round(progress)}% завершено
          </div>
        </div>

        {/* Шаги процесса */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Этапы генерации:</h4>
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                step.status === 'active' ? 'ring-2 ring-blue-200' : ''
              }`}
            >
              <div className={`flex-shrink-0 ${getStepColor(step).split(' ')[0]}`}>
                {getStepIcon(step)}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h5 className={`text-sm font-medium ${getStepColor(step).split(' ')[0]}`}>
                    {step.title}
                  </h5>
                  {step.status === 'active' && (
                    <span className="text-xs text-blue-600 animate-pulse">
                      В процессе...
                    </span>
                  )}
                  {step.status === 'completed' && (
                    <span className="text-xs text-green-600">
                      Завершено
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {step.description}
                </p>
              </div>
              
              {step.status === 'active' && (
                <div className="flex-shrink-0">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Дополнительная информация */}
        <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-800">
            <Clock size={14} />
            <span>
              Осталось примерно {Math.max(0, estimatedTime - elapsedTime)} секунд
            </span>
          </div>
          <p className="text-xs text-blue-600 mt-1">
            GPT-5 использует reasoning для создания максимально качественных кластеров
          </p>
        </div>
      </div>
    </div>
  )
}
