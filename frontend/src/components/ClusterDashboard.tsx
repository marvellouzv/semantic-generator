import React from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Label } from 'recharts'
import { BarChart3, PieChart as PieChartIcon, TrendingUp, Hash, Tag } from 'lucide-react'
import type { UpperGraph } from '../types'

interface Props {
  upperGraph: UpperGraph
}

interface IntentData {
  name: string
  value: number
  color: string
}

interface CategoryData {
  name: string
  value: number
  color: string
}

interface DemandData {
  level: string
  count: number
  color: string
}

interface DemandDonutData {
  name: string
  value: number
  color: string
}

interface ParentThemeData {
  name: string
  value: number
  color: string
}

const INTENT_COLORS = {
  commercial: '#3B82F6',      // Синий
  informational: '#10B981',   // Зеленый
  service: '#F59E0B',         // Оранжевый
  price: '#EF4444',           // Красный
  local: '#8B5CF6',           // Фиолетовый
  urgent: '#F97316',          // Оранжево-красный
  reviews: '#06B6D4',         // Голубой
  comparative: '#84CC16',     // Лайм
  diy: '#EC4899',             // Розовый
  download: '#6366F1',        // Индиго
  technical: '#14B8A6',       // Бирюзовый (Teal)
  legal: '#F43F5E',           // Розово-красный
  brand: '#8B5CF6',           // Фиолетовый
  navigational: '#F59E0B',    // Оранжевый
  problem: '#EF4444',         // Красный
  // Добавляем больше цветов для других возможных интентов
  transactional: '#8B5CF6',   // Фиолетовый (был зеленый - изменен)
  unknown: '#6B7280'          // Серый для неизвестных
}

const DEMAND_COLORS = {
  'Высокий': '#EF4444',  // Red
  'High': '#EF4444',
  'Средний': '#F59E0B',  // Orange
  'Medium': '#F59E0B',
  'Низкий': '#6B7280',   // Gray
  'Low': '#6B7280'
}

// Палитра для "родительской категории (выбранные типы)".
// Важно: НЕ используем синий/зелёный из диаграммы интентов и избегаем повторов.
const CATEGORY_PALETTE = [
  // Более контрастные оттенки (и меньше "почти одинаковых красных")
  // Важно: НЕ используем синий/зелёный, чтобы не пересекаться с диаграммой интентов.
  '#F59E0B', // amber
  '#A855F7', // purple
  '#EF4444', // red
  '#F97316', // orange
  '#EC4899', // pink
  '#7C3AED', // violet
  '#A16207', // brown-ish
  '#64748B', // slate
  '#D946EF', // fuchsia
  '#FB7185', // light rose
]

const THEME_PALETTE = [
  '#8B5CF6', // violet
  '#A855F7', // purple
  '#EC4899', // pink
  '#F97316', // orange
  '#F59E0B', // amber
  '#EF4444', // red
  '#64748B', // slate
  '#A3A3A3', // neutral
]

// Маппинг интентов: английский -> русский
const INTENT_NAMES: Record<string, string> = {
  commercial: 'Коммерческие',
  informational: 'Информационные',
  service: 'Услуги',
  price: 'Ценовые',
  local: 'Локальные',
  urgent: 'Срочные',
  reviews: 'Отзывы',
  comparative: 'Сравнительные',
  diy: 'Сделай сам',
  download: 'Скачать',
  technical: 'Технические',
  legal: 'Юридические',
  brand: 'Брендовые',
  navigational: 'Навигационные',
  problem: 'Проблемные',
  transactional: 'Транзакционные',
  unknown: 'Неизвестные'
}

// Маппинг уровней спроса
const DEMAND_LEVEL_NAMES: Record<string, string> = {
  'High': 'Высокий',
  'Высокий': 'Высокий',
  'Medium': 'Средний',
  'Средний': 'Средний',
  'Low': 'Низкий',
  'Низкий': 'Низкий'
}

// Функция для нормализации интентов
const normalizeIntent = (intent: string): string => {
  if (!intent) return 'unknown'
  const lower = intent.toLowerCase()
  
  // Если уже на русском
  for (const [key, value] of Object.entries(INTENT_NAMES)) {
    if (lower === value.toLowerCase()) return key
  }
  
  // Если на английском
  if (INTENT_NAMES[lower]) return lower
  
  return 'unknown'
}

// Нормализация родительской категории (русская категория -> ключ интента)
const normalizeCategoryKey = (category: string): string => {
  if (!category) return 'unknown'
  const lower = category.toLowerCase().trim()

  // Если передали ключ интента
  if (INTENT_NAMES[lower]) return lower

  // Если передали русское название категории
  for (const [key, value] of Object.entries(INTENT_NAMES)) {
    if (lower === value.toLowerCase()) return key
  }

  return 'unknown'
}

// Функция для нормализации уровней спроса
const normalizeDemandLevel = (level: string): string => {
  if (!level) return 'Unknown'
  return DEMAND_LEVEL_NAMES[level] || level
}

// Custom Tooltip для Pie Chart - показывает интент и количество
const CustomPieTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
        <p className="font-semibold text-gray-800">{data.name}</p>
        <p className="text-sm text-gray-600">{data.value} кластеров</p>
      </div>
    )
  }
  return null
}

const wrapLabel = (label: string, maxLen = 18, maxLines = 3): string[] => {
  const words = (label || '').split(/\s+/).filter(Boolean)
  if (!words.length) return ['']
  const lines: string[] = []
  let current = ''
  for (const w of words) {
    const next = current ? `${current} ${w}` : w
    if (next.length <= maxLen) {
      current = next
      continue
    }
    if (current) lines.push(current)
    current = w
    if (lines.length >= maxLines - 1) break
  }
  if (current && lines.length < maxLines) lines.push(current)
  if (lines.length >= maxLines && words.join(' ').length > lines.join(' ').length) {
    const last = lines[maxLines - 1]
    lines[maxLines - 1] = last.length > maxLen - 1 ? `${last.slice(0, Math.max(0, maxLen - 1))}…` : `${last}…`
  }
  return lines
}

const YAxisWrappedTick = (props: any) => {
  const { x, y, payload } = props
  const lines = wrapLabel(String(payload?.value ?? ''), 18, 3)
  return (
    <text x={x} y={y} textAnchor="end" fill="#374151" fontSize={12}>
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? 0 : 14}>
          {line}
        </tspan>
      ))}
    </text>
  )
}

const ChartCard = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="bg-gray-50 rounded-lg p-4 h-[360px] flex flex-col">
    <h3 className="text-lg font-semibold mb-3 text-gray-800">{title}</h3>
    <div className="flex-1 min-h-0">{children}</div>
  </div>
)

const DonutWithLegend = ({
  data,
  totalLabel,
}: {
  data: Array<{ name: string; value: number; color: string }>
  totalLabel: string
}) => {
  const total = data.reduce((s, d) => s + (d.value || 0), 0)
  return (
    <div className="h-full grid grid-cols-1 md:grid-cols-[1fr_220px] gap-2 items-center">
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={95}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`donut-cell-${index}`} fill={entry.color} />
              ))}
              <Label
                position="center"
                content={() => (
                  <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle">
                    <tspan x="50%" dy="-4" fontSize="18" fontWeight="700" fill="#111827">
                      {total}
                    </tspan>
                    <tspan x="50%" dy="18" fontSize="12" fill="#6B7280">
                      {totalLabel}
                    </tspan>
                  </text>
                )}
              />
            </Pie>
            <Tooltip content={<CustomPieTooltip />} cursor={{ fill: 'rgba(0, 0, 0, 0.06)' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="max-h-[260px] overflow-auto pr-1">
        <div className="space-y-2">
          {data
            .slice()
            .sort((a, b) => b.value - a.value)
            .map((item) => {
              const pct = total > 0 ? Math.round((item.value / total) * 100) : 0
              return (
                <div key={item.name} className="flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-gray-700">{item.name}</div>
                    <div className="text-xs text-gray-500">
                      {item.value} • {pct}%
                    </div>
                  </div>
                </div>
              )
            })}
        </div>
      </div>
    </div>
  )
}

export default function ClusterDashboard({ upperGraph }: Props) {
  // Prepare data for charts
  const intentData: IntentData[] = React.useMemo(() => {
    const intentCounts: Record<string, number> = {}
    
    upperGraph.clusters.forEach(cluster => {
      // Intent (GPT) is a simple 3-class value: commercial / informational / unknown
      let primaryIntent = normalizeIntent(cluster.gpt_intent || 'unknown')
      if (primaryIntent !== 'commercial' && primaryIntent !== 'informational') {
        primaryIntent = 'unknown'
      }
      
      // Count only once per cluster
      intentCounts[primaryIntent] = (intentCounts[primaryIntent] || 0) + 1
    })
    
    // Filter out 'unknown' if we have real intents
    const hasRealIntents = Object.keys(intentCounts).some(k => k !== 'unknown')
    if (hasRealIntents && intentCounts['unknown']) {
      delete intentCounts['unknown']
    }
    
    return Object.entries(intentCounts).map(([intent, count]) => {
      const color = INTENT_COLORS[intent as keyof typeof INTENT_COLORS] || '#6B7280'
      return {
        name: INTENT_NAMES[intent] || intent, // Используем русское имя
        value: count,
        color
      }
    })
  }, [upperGraph.clusters])

  const categoryData: CategoryData[] = React.useMemo(() => {
    const categoryCounts: Record<string, number> = {}

    upperGraph.clusters.forEach(cluster => {
      // Group (selected types) comes from parent_category; fallback to intent_mix if needed
      const categoryName =
        (cluster as any).parent_category ||
        (Array.isArray(cluster.intent_mix) && cluster.intent_mix[0] ? (INTENT_NAMES[cluster.intent_mix[0] as keyof typeof INTENT_NAMES] || cluster.intent_mix[0]) : 'Неизвестные')
      categoryCounts[categoryName] = (categoryCounts[categoryName] || 0) + 1
    })

    // Keep stable ordering by count desc
    return Object.entries(categoryCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count], index) => {
        const color = CATEGORY_PALETTE[index % CATEGORY_PALETTE.length]
        return { name, value: count, color }
      })
  }, [upperGraph.clusters])

  const demandData: DemandData[] = React.useMemo(() => {
    const demandCounts: Record<string, number> = {}
    
    upperGraph.clusters.forEach(cluster => {
      const level = normalizeDemandLevel(cluster.demand_level || 'Unknown')
      demandCounts[level] = (demandCounts[level] || 0) + 1
    })
    
    return Object.entries(demandCounts).map(([level, count]) => ({
      level,
      count,
      color: DEMAND_COLORS[level as keyof typeof DEMAND_COLORS] || '#6B7280'
    }))
  }, [upperGraph.clusters])

  const demandDonutData: DemandDonutData[] = React.useMemo(() => {
    const mapLabel: Record<string, string> = {
      High: 'Высокий',
      Medium: 'Средний',
      Low: 'Низкий',
      Высокий: 'Высокий',
      Средний: 'Средний',
      Низкий: 'Низкий',
    }
    return demandData
      .slice()
      .map((d) => ({
        name: mapLabel[d.level] || d.level,
        value: d.count,
        color: d.color,
      }))
  }, [demandData])

  const parentThemes = React.useMemo(() => {
    const themes = new Set(upperGraph.clusters.map(c => c.parent_theme).filter(Boolean))
    return Array.from(themes)
  }, [upperGraph.clusters])

  const parentThemeData: ParentThemeData[] = React.useMemo(() => {
    const counts: Record<string, number> = {}
    upperGraph.clusters.forEach(c => {
      const t = (c.parent_theme || '').trim()
      if (!t) return
      counts[t] = (counts[t] || 0) + 1
    })
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 25)
      .map(([name, value], index) => ({ name, value, color: THEME_PALETTE[index % THEME_PALETTE.length] }))
  }, [upperGraph.clusters])

  const totalClusters = upperGraph.clusters.length
  const highDemandCount = upperGraph.clusters.filter(c => c.demand_level === 'High').length
  const commercialCount = upperGraph.clusters.filter(c => {
    // Check if cluster has commercial or price intent in gpt_intent or intent_mix
    if (c.gpt_intent === 'commercial' || c.gpt_intent === 'price' || c.gpt_intent === 'коммерческие') {
      return true
    }
    if (c.intent_mix && (c.intent_mix.includes('commercial') || c.intent_mix.includes('price'))) {
      return true
    }
    return false
  }).length
  
  // Debug: проверим что приходит в данных
  // console.log('Debug ClusterDashboard:', {
  //   totalClusters,
  //   commercialCount,
  //   sampleClusters: upperGraph.clusters.slice(0, 3).map(c => ({
  //     name: c.name,
  //     gpt_intent: c.gpt_intent,
  //     intent_mix: c.intent_mix
  //   }))
  // })

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center gap-2 mb-6">
        <BarChart3 className="h-6 w-6 text-blue-600" />
        <h2 className="text-xl font-semibold">Аналитика кластеров</h2>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Hash className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-800">Всего кластеров</span>
          </div>
          <div className="text-2xl font-bold text-blue-900">{totalClusters}</div>
        </div>

        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <span className="text-sm font-medium text-green-800">Высокий спрос</span>
          </div>
          <div className="text-2xl font-bold text-green-900">{highDemandCount}</div>
          <div className="text-xs text-green-600">
            {totalClusters > 0 ? Math.round((highDemandCount / totalClusters) * 100) : 0}% от общего
          </div>
        </div>

        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Tag className="h-5 w-5 text-slate-700" />
            <span className="text-sm font-medium text-slate-800">Коммерческие</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{commercialCount}</div>
          <div className="text-xs text-slate-700">
            {totalClusters > 0 ? Math.round((commercialCount / totalClusters) * 100) : 0}% от общего
          </div>
        </div>

        <div className="bg-orange-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <PieChartIcon className="h-5 w-5 text-orange-600" />
            <span className="text-sm font-medium text-orange-800">Тем</span>
          </div>
          <div className="text-2xl font-bold text-orange-900">{parentThemes.length}</div>
          <div className="text-xs text-orange-600">Родительских тем</div>
        </div>
      </div>

      {/* Charts: row 1 (2 columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Intent Distribution Pie Chart */}
        <ChartCard title="Распределение по интентам (primary intent от GPT)">
          <DonutWithLegend data={intentData} totalLabel="кластеров" />
        </ChartCard>

        {/* Parent Category Pie Chart */}
        <ChartCard title="Распределение по родительской категории (выбранные типы)">
          <DonutWithLegend data={categoryData} totalLabel="кластеров" />
        </ChartCard>

      </div>

      {/* Charts: row 2 (2 columns) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Demand Level Bar Chart */}
        <ChartCard title="Уровни спроса">
          <DonutWithLegend data={demandDonutData} totalLabel="кластеров" />
        </ChartCard>

        {/* Parent Theme Top Table */}
        <ChartCard title="Топ родительских тем (Parent Theme от GPT)">
          <div className="h-full flex flex-col">
            <div className="text-xs text-gray-500 mb-2">Топ‑25 тем по числу кластеров</div>
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden flex-1 min-h-0">
              <div className="grid grid-cols-[1fr_96px] gap-2 px-3 py-2 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600 sticky top-0 z-10">
                <div>Тема</div>
                <div className="text-right">Кластеры</div>
              </div>
              <div className="overflow-auto max-h-[260px]">
                {parentThemeData.length === 0 ? (
                  <div className="p-3 text-sm text-gray-500">Нет данных</div>
                ) : (
                  parentThemeData.map((row, idx) => (
                    <div
                      key={`${row.name}-${idx}`}
                      className="grid grid-cols-[1fr_96px] gap-2 px-3 py-2 border-b border-gray-100 last:border-b-0"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: row.color }} />
                          <span className="text-sm text-gray-800 break-words">{row.name}</span>
                        </div>
                      </div>
                      <div className="text-right text-sm font-semibold text-gray-900">{row.value}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </ChartCard>
      </div>
    </div>
  )
}

