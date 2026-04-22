import React, { useState, useEffect, useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Trash2, Upload } from 'lucide-react'
import type { Intent, UpperGraphRequest, ClusterTemplate, UpperGraph } from '../types'
import apiService from '../api'
import ValidationFeedback from './ValidationFeedback'
import BulkUploadModal from './BulkUploadModal'
import { useTopicValidation } from '../utils/validation'

const INTENT_CONFIG: Array<{
  id: Intent
  label: string
  description: string
  examples: string[]
}> = [
  {
    id: 'commercial',
    label: 'Коммерческие',
    description: 'Покупка, заказ услуг',
    examples: ['купить', 'заказать', 'цена']
  },
  {
    id: 'informational',
    label: 'Информационные',
    description: 'Обучение, справка',
    examples: ['что такое', 'как работает', 'виды']
  },
  {
    id: 'service',
    label: 'Сервисные',
    description: 'Ремонт, установка',
    examples: ['ремонт', 'установка', 'обслуживание']
  },
  {
    id: 'price',
    label: 'Ценовые',
    description: 'Стоимость, тарифы',
    examples: ['стоимость', 'расценки', 'сколько стоит']
  },
  {
    id: 'local',
    label: 'Локальные',
    description: 'Поиск рядом',
    examples: ['рядом', 'в городе', 'адрес']
  },
  {
    id: 'urgent',
    label: 'Срочные',
    description: 'Быстрое решение',
    examples: ['срочно', 'быстро', '24/7']
  },
  {
    id: 'reviews',
    label: 'Отзывы',
    description: 'Мнения, опыт',
    examples: ['отзывы', 'мнения', 'опыт']
  },
  {
    id: 'comparative',
    label: 'Сравнительные',
    description: 'Выбор лучшего',
    examples: ['лучший', 'сравнить', 'рейтинг']
  },
  {
    id: 'diy',
    label: 'Своими руками',
    description: 'Самостоятельное выполнение',
    examples: ['как сделать', 'инструкция', 'пошагово']
  },
  {
    id: 'download',
    label: 'Загрузки',
    description: 'Файлы, документы',
    examples: ['скачать', 'документация', 'схема']
  },
  {
    id: 'technical',
    label: 'Технические',
    description: 'Характеристики, спецификации',
    examples: ['параметры', 'технические данные', 'свойства']
  },
  {
    id: 'legal',
    label: 'Правовые',
    description: 'Лицензии, нормативы',
    examples: ['лицензия', 'сертификат', 'требования']
  },
  {
    id: 'brand',
    label: 'Брендовые',
    description: 'Конкретные марки',
    examples: ['производители', 'бренды', 'марки']
  },
  {
    id: 'navigational',
    label: 'Навигационные',
    description: 'Поиск сайтов, контактов',
    examples: ['официальный сайт', 'контакты', 'телефон']
  },
  {
    id: 'problem',
    label: 'Проблемные',
    description: 'Неисправности, ошибки',
    examples: ['не работает', 'сломался', 'проблема']
  }
]

const ALL_INTENTS: Intent[] = INTENT_CONFIG.map(config => config.id)

const setupSchema = z.object({
  topic: z.string()
    .min(1, 'Введите тематику')
    .refine((val) => val.trim().length > 0, 'Тематика не может быть пустой')
    .refine((val) => {
      // Проверяем, что есть хотя бы одна тема (до или после запятой)
      const themes = val.split(',').map(t => t.trim()).filter(t => t.length > 0)
      return themes.length > 0
    }, 'Введите хотя бы одну тему'),
  intents: z.array(z.string()).min(1, 'Выберите хотя бы один тип запроса'),
  brand_whitelist: z.string().optional(),
  minus_words: z.string().optional(),
  regions: z.string().optional()
})

type SetupFormData = z.infer<typeof setupSchema>

interface Props {
  onSubmit: (data: UpperGraphRequest) => void
  onTemplateLoad: (upperGraph: UpperGraph) => void
  loading: boolean
}

export default function SetupScreen({ onSubmit, onTemplateLoad, loading }: Props) {
  const [templates, setTemplates] = useState<ClusterTemplate[]>([])
  const [loadingTemplates, setLoadingTemplates] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [templateMode, setTemplateMode] = useState<'use' | 'expand'>('use')
  const [showBulkUpload, setShowBulkUpload] = useState(false)
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors }
  } = useForm<SetupFormData>({
    resolver: zodResolver(setupSchema),
    defaultValues: {
      topic: 'ремонт окон',
      intents: ['commercial', 'informational', 'service', 'price', 'local'],
      brand_whitelist: ''
    }
  })

  const selectedIntents = watch('intents')
  const topic = watch('topic')
  const regionsRaw = watch('regions')

  // Debounced validation to avoid too many re-renders
  const [debouncedTopic, setDebouncedTopic] = useState(topic)
  const [debouncedIntents, setDebouncedIntents] = useState(selectedIntents)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTopic(topic)
    }, 300)
    return () => clearTimeout(timer)
  }, [topic])

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedIntents(selectedIntents)
    }, 300)
    return () => clearTimeout(timer)
  }, [selectedIntents])

  // Real-time validation
  const validation = useTopicValidation(debouncedTopic, debouncedIntents)

  // Загрузка шаблонов при монтировании компонента
  useEffect(() => {
    const loadTemplates = async () => {
      setLoadingTemplates(true)
      try {
        const response = await apiService.listTemplates()
        setTemplates(response.templates)
      } catch (error) {
        console.error('Ошибка загрузки шаблонов:', error)
      } finally {
        setLoadingTemplates(false)
      }
    }

    loadTemplates()
  }, [])


  const handleTemplateSelect = async (templateId: string) => {
    if (!templateId) {
      setSelectedTemplate('')
      return
    }

    setSelectedTemplate(templateId)
    
    // Если режим "Использовать" - сразу загружаем шаблон
    if (templateMode === 'use') {
      try {
        const upperGraph = await apiService.getTemplateAsUpperGraph(templateId)
        onTemplateLoad(upperGraph)
      } catch (error) {
        console.error('Ошибка загрузки шаблона:', error)
        alert('Ошибка при загрузке шаблона')
      }
    }
    // Если режим "Дополнить" - просто выбираем шаблон, но не загружаем
  }

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Удалить этот шаблон?')) return

    try {
      await apiService.deleteTemplate(templateId)
      setTemplates(prev => prev.filter(t => t.id !== templateId))
      if (selectedTemplate === templateId) {
        setSelectedTemplate('')
      }
      alert('Шаблон удален')
    } catch (error) {
      console.error('Ошибка удаления шаблона:', error)
      alert('Ошибка при удалении шаблона')
    }
  }

  const toggleIntent = (intent: Intent) => {
    const current = selectedIntents
    const updated = current.includes(intent)
      ? current.filter(i => i !== intent)
      : [...current, intent]
    setValue('intents', updated)
  }

  const handleBulkUpload = async (queries: string[], intents: string[]) => {
    if (queries.length === 0) {
      alert('Нет запросов для загрузки')
      return
    }

    // For batch processing, we need to send to backend
    // This will trigger batch API with each query processed individually
    try {
      const minusWordsRaw = (watch('minus_words') || '').trim()
      const minusWords = minusWordsRaw
        ? minusWordsRaw
            .split(/[\n,;]/g)
            .map(w => w.trim())
            .filter(Boolean)
        : undefined

      const regions = regionsRaw
        ? regionsRaw
            .split(/[\n,;]/g)
            .map(r => r.trim())
            .filter(Boolean)
        : undefined

      const request: UpperGraphRequest = {
        topic: topic,
        locale: 'ru-RU',
        intents: intents as Intent[],
        bulk_queries: queries,  // New field for batch processing
        minus_words: minusWords,
        regions
      }
      onSubmit(request)
    } catch (error) {
      console.error('Ошибка при загрузке запросов:', error)
      alert('Ошибка при загрузке запросов')
    }
  }

  const handleFormSubmit = (data: SetupFormData) => {
    const brandWhitelist = data.brand_whitelist
      ? data.brand_whitelist.split(',').map(b => b.trim()).filter(b => b)
      : undefined

    const minusWords = data.minus_words
      ? data.minus_words
          .split(/[\n,;]/g)
          .map(w => w.trim())
          .filter(Boolean)
      : undefined

    const regions = data.regions
      ? data.regions
          .split(/[\n,;]/g)
          .map(r => r.trim())
          .filter(Boolean)
      : undefined

    const request: UpperGraphRequest = {
      topic: data.topic,
      locale: 'ru-RU', // Всегда используем ru-RU
      intents: data.intents as Intent[],
      brand_whitelist: brandWhitelist,
      template_id: (templateMode === 'expand' && selectedTemplate) ? selectedTemplate : undefined,
      minus_words: minusWords,
      regions
    }
    onSubmit(request)
  }

  return (
    <div className="max-w-5xl mx-auto p-6 md:p-8">
      <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4 text-slate-900">Semantic Generator</h1>
      

      <div className="bg-white rounded-xl p-6 md:p-8">
        <h2 className="text-xl font-semibold tracking-tight mb-6 text-slate-900">
          {selectedTemplate ? 'Информация о шаблоне' : 'Настройка генерации'}
        </h2>
        
        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">
              Тематика *
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                Множественные темы
              </span>
            </label>
            <input
              {...register('topic')}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Например: ремонт окон, установка дверей, остекление балконов"
            />
            <p className="text-xs text-gray-500 mt-1">
              💡 Можно указать несколько тем через запятую для комплексного покрытия
              <br />
              <span className="text-gray-400">
                Примеры: "детские врачи, педиатры, детские болезни" или "ремонт окон, установка дверей"
              </span>
            </p>
            {errors.topic && (
              <p className="text-red-500 text-sm mt-1">{errors.topic.message}</p>
            )}
            
            {/* Real-time validation feedback */}
            {topic && (
              <div className="mt-3">
                <ValidationFeedback validation={validation} />
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-3">
              Типы запросов *
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {INTENT_CONFIG.map((intentConfig) => (
                <label
                  key={intentConfig.id}
                  className={`flex flex-col p-3 border rounded-lg cursor-pointer transition-all duration-200 ${
                    selectedIntents.includes(intentConfig.id)
                      ? 'bg-blue-50 border-blue-300 shadow-sm'
                      : 'bg-slate-50 border-slate-200 hover:bg-slate-100 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIntents.includes(intentConfig.id)}
                    onChange={() => toggleIntent(intentConfig.id)}
                    className="sr-only"
                  />
                  
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-gray-900">
                      {intentConfig.label}
                    </span>
                    <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                      selectedIntents.includes(intentConfig.id)
                        ? 'bg-blue-600 border-blue-600'
                        : 'border-slate-300'
                    }`}>
                      {selectedIntents.includes(intentConfig.id) && (
                        <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  </div>
                  
                  <p className="text-xs text-gray-600 mb-2">
                    {intentConfig.description}
                  </p>
                  
                  <div className="flex flex-wrap gap-1">
                    {intentConfig.examples.map((example, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 bg-slate-200 text-slate-700 text-xs rounded"
                      >
                        {example}
                      </span>
                    ))}
                  </div>
                </label>
              ))}
            </div>
            {errors.intents && (
              <p className="text-red-500 text-sm mt-2">{errors.intents.message}</p>
            )}
            
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                💡 <strong>Совет:</strong> Выберите 3-5 типов для оптимального результата. 
                Больше типов = больше разнообразия кластеров.
              </p>
            </div>
            
            {selectedIntents.includes('brand') && (
              <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <label className="block text-sm font-medium mb-2 text-slate-800">
                  🏷️ Список брендов (через запятую)
                </label>
                <input
                  {...register('brand_whitelist')}
                  className="w-full p-3 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Например: Rehau, KBE, Veka, Schuco"
                />
                <p className="text-xs text-slate-600 mt-1">
                  Укажите бренды, которые должны быть включены в генерацию. Если поле пустое, брендовые кластеры генерироваться не будут.
                </p>
                {errors.brand_whitelist && (
                  <p className="text-red-500 text-sm mt-1">{errors.brand_whitelist.message}</p>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <label className="block text-sm font-medium mb-2 text-gray-800">
                🚫 Минус-слова (через запятую или с новой строки)
              </label>
              <textarea
                {...register('minus_words')}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[96px]"
                placeholder={"Например:\nбесплатно\nскачать\nвакансия, работа"}
              />
              <p className="text-xs text-gray-600 mt-1">
                Эти слова/фразы не должны встречаться в head-запросах (и в локальных вариациях тоже).
              </p>
            </div>

            <div className={`p-4 border rounded-lg ${selectedIntents.includes('local') ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200 opacity-70'}`}>
              <label className="block text-sm font-medium mb-2 text-gray-800">
                📍 Регионы для локальных запросов
              </label>
              <textarea
                {...register('regions')}
                disabled={!selectedIntents.includes('local')}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[96px] disabled:bg-gray-100"
                placeholder={"Например:\nСанкт-Петербург\nМосква"}
              />
              <p className="text-xs text-gray-600 mt-1">
                Если выбран тип <strong>Локальные</strong> и указаны регионы — локальные запросы будут генерироваться <strong>только</strong> для этих регионов,
                включая вариации (“СПб”, “Питер”, “в СПб” и т.д.).
                Если регионы не указаны — будут использоваться общие локальные слова (“рядом”, “в городе”) без конкретных городов.
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setShowBulkUpload(true)}
              disabled={loading}
              className="px-6 py-3 bg-slate-700 text-white rounded-md hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <Upload size={18} />
              Массовая загрузка
            </button>
            <button
              type="submit"
              disabled={loading || !validation.isValid || (templateMode === 'expand' && (!selectedTemplate || templates.length === 0))}
              className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 
                (templateMode === 'expand' ? 'Дополнение...' : 'Генерация...') : 
                (templateMode === 'expand' && selectedTemplate ? 
                  'Дополнить шаблон' : 
                  'Сгенерировать кластеры'
                )
              }
            </button>
          </div>
        </form>
      </div>

      <BulkUploadModal
        isOpen={showBulkUpload}
        onClose={() => setShowBulkUpload(false)}
        onUpload={handleBulkUpload}
        selectedIntents={selectedIntents}
      />
    </div>
  )
}
