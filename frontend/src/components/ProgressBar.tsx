import React, { useState, useEffect } from 'react'
import { apiService } from '../api'

interface ProgressState {
  current: number
  total: number
  status: 'idle' | 'running' | 'completed' | 'error'
  message: string
}

interface Props {
  isActive: boolean
  onComplete?: () => void
  onError?: (error: string) => void
}

export default function ProgressBar({ isActive, onComplete, onError }: Props) {
  const [progress, setProgress] = useState<ProgressState>({
    current: 0,
    total: 0,
    status: 'idle',
    message: ''
  })

  useEffect(() => {
    if (!isActive) {
      setProgress({ current: 0, total: 0, status: 'idle', message: '' })
      return
    }

    let eventSource: EventSource | null = null
    let pollInterval: NodeJS.Timeout | null = null

    const startTracking = () => {
      // Используем простой polling
      startPolling()
    }

    const startPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const data = await apiService.getProgress()
          setProgress(data)
          
          if (data.status === 'completed') {
            onComplete?.()
            if (pollInterval) clearInterval(pollInterval)
          } else if (data.status === 'error') {
            onError?.(data.message)
            if (pollInterval) clearInterval(pollInterval)
          }
        } catch (e) {
          console.error('Error polling progress:', e)
        }
      }, 1000)
    }

    startTracking()

    return () => {
      eventSource?.close()
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [isActive, onComplete, onError])

  if (!isActive || progress.status === 'idle') {
    return null
  }

  const percentage = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0

  return (
    <div className="w-full max-w-md mx-auto p-4 bg-white rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">Генерация запросов</h3>
        <span className="text-sm text-gray-500">
          {progress.current}/{progress.total}
        </span>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
        <div
          className={`h-3 rounded-full transition-all duration-300 ${
            progress.status === 'error' ? 'bg-red-500' : 
            progress.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600">{progress.message}</span>
        <span className="font-medium">{percentage}%</span>
      </div>
      
      {progress.status === 'running' && (
        <div className="mt-3 flex items-center justify-center">
          <div className="loading-spinner"></div>
          <span className="ml-2 text-sm text-gray-500">Обработка...</span>
        </div>
      )}
      
      {progress.status === 'completed' && (
        <div className="mt-3 text-center text-green-600 font-medium">
          ✅ Генерация завершена!
        </div>
      )}
      
      {progress.status === 'error' && (
        <div className="mt-3 text-center text-red-600 font-medium">
          ❌ Произошла ошибка
        </div>
      )}
    </div>
  )
}
