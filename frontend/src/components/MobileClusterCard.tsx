import React from 'react'
import { Edit2, Trash2 } from 'lucide-react'
import type { UpperCluster } from '../types'

interface Props {
  cluster: UpperCluster
  isSelected: boolean
  onSelect: (clusterId: string, selected: boolean) => void
  onEdit: (clusterId: string) => void
  onDelete: (clusterId: string) => void
}

export default function MobileClusterCard({ 
  cluster, 
  isSelected, 
  onSelect, 
  onEdit, 
  onDelete 
}: Props) {
  const demandLevel = cluster.demand_level
  const rowColorClass = {
    'High': 'bg-red-50 border-red-200',
    'Medium': 'bg-yellow-50 border-yellow-200', 
    'Low': 'bg-gray-50 border-gray-200'
  }[demandLevel as keyof typeof rowColorClass] || 'bg-white border-gray-200'
  
  return (
    <div className={`border-b p-4 ${rowColorClass}`}>
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-gray-900 text-sm leading-tight flex-1 pr-2">
          {cluster.name}
        </h3>
        <div className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onSelect(cluster.cluster_id, e.target.checked)}
            className="rounded border-gray-300"
            aria-label={`Выбрать кластер ${cluster.name}`}
          />
        </div>
      </div>
      
      <div className="space-y-2 text-xs text-gray-600">
        <div className="flex items-center gap-2">
          <span className="font-medium">Интент:</span>
          <span className={`px-2 py-1 rounded text-xs ${
            cluster.gpt_intent === 'commercial' ? 'bg-green-100 text-green-800' :
            cluster.gpt_intent === 'informational' ? 'bg-blue-100 text-blue-800' :
            cluster.gpt_intent === 'transactional' ? 'bg-slate-100 text-slate-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {cluster.gpt_intent || 'N/A'}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="font-medium">Спрос:</span>
          <span className={`px-2 py-1 rounded text-xs ${
            demandLevel === 'High' ? 'bg-red-100 text-red-800' :
            demandLevel === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {demandLevel || 'N/A'}
          </span>
        </div>
        
        {cluster.parent_theme && (
          <div className="flex items-start gap-2">
            <span className="font-medium">Тема:</span>
            <span className="text-gray-700 flex-1">{cluster.parent_theme}</span>
          </div>
        )}
        
        {cluster.tags && cluster.tags.length > 0 && (
          <div className="flex items-start gap-2">
            <span className="font-medium">Теги:</span>
            <div className="flex flex-wrap gap-1 flex-1">
              {cluster.tags.map((tag, index) => (
                <span key={index} className="px-1 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {cluster.notes && (
          <div className="flex items-start gap-2">
            <span className="font-medium">Заметки:</span>
            <span className="text-gray-700 flex-1 text-xs">{cluster.notes}</span>
          </div>
        )}
      </div>
      
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onEdit(cluster.cluster_id)}
            className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
            aria-label={`Редактировать кластер ${cluster.name}`}
          >
            <Edit2 size={16} />
          </button>
          <button
            onClick={() => onDelete(cluster.cluster_id)}
            className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded"
            aria-label={`Удалить кластер ${cluster.name}`}
          >
            <Trash2 size={16} />
          </button>
        </div>
        
        <div className="text-xs text-gray-500">
          {cluster.seed_examples?.length || 0} примеров
        </div>
      </div>
    </div>
  )
}
