import React from 'react'
import { AlertCircle, CheckCircle, Info, Clock, Zap, TrendingUp } from 'lucide-react'
import type { ValidationResult } from '../utils/validation'

interface Props {
  validation: ValidationResult
  showSuggestions?: boolean
}

export default function ValidationFeedback({ validation, showSuggestions = true }: Props) {
  const { errors, warnings, suggestions, complexityScore, estimatedTime, isValid } = validation

  if (isValid && errors.length === 0 && warnings.length === 0 && !showSuggestions) {
    return null
  }

  return (
    <div className="space-y-3">
      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-2">Ошибки валидации</h4>
              <ul className="space-y-1">
                {errors.map((error, index) => (
                  <li key={index} className="text-sm text-red-700">• {error}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-yellow-800 mb-2">Предупреждения</h4>
              <ul className="space-y-1">
                {warnings.map((warning, index) => (
                  <li key={index} className="text-sm text-yellow-700">• {warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Suggestions */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-blue-800 mb-2">Рекомендации</h4>
              <ul className="space-y-1">
                {suggestions.map((suggestion, index) => (
                  <li key={index} className="text-sm text-blue-700">• {suggestion}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Complexity and Time Info */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Complexity Score */}
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-gray-600" />
              <span className="text-sm text-gray-700">Сложность:</span>
              <div className="flex items-center gap-1">
                <div className="w-16 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      complexityScore < 30 ? 'bg-green-500' :
                      complexityScore < 60 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${complexityScore}%` }}
                  />
                </div>
                <span className="text-xs text-gray-600 font-medium">{complexityScore}%</span>
              </div>
            </div>

            {/* Estimated Time */}
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-600" />
              <span className="text-sm text-gray-700">Время:</span>
              <span className="text-sm font-medium text-gray-800">{estimatedTime}</span>
            </div>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            {isValid ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-green-700 font-medium">Готово к генерации</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 text-red-600" />
                <span className="text-sm text-red-700 font-medium">Требуются исправления</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
