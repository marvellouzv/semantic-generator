import type { UpperGraph, UpperCluster } from '../types'
import { API_BASE_URL } from '../api'

export interface GenerationHistory {
  id: string
  timestamp: number
  topic: string
  intents: string[]
  locale: string
  upperGraph: UpperGraph
  metadata: {
    generationTime: number
    clusterCount: number
    highDemandCount: number
    commercialCount: number
    parentThemes: string[]
  }
  version: number
  isActive: boolean
}

export interface HistoryComparison {
  id1: string
  id2: string
  differences: {
    addedClusters: UpperCluster[]
    removedClusters: UpperCluster[]
    modifiedClusters: {
      cluster: UpperCluster
      changes: Record<string, { old: any; new: any }>
    }[]
    metadataChanges: Record<string, { old: any; new: any }>
  }
}

class HistoryManager {
  private baseUrl = API_BASE_URL

  async init(): Promise<void> {
    // No-op: backend storage does not require client initialization.
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {})
      }
    })

    if (!response.ok) {
      const text = await response.text().catch(() => '')
      throw new Error(text || `HTTP ${response.status}`)
    }

    return response.json() as Promise<T>
  }

  async saveGeneration(upperGraph: UpperGraph, topic: string, intents: string[], locale: string, generationTime: number): Promise<string> {
    const saved = await this.request<GenerationHistory>('/api/v1/history', {
      method: 'POST',
      body: JSON.stringify({
        upperGraph,
        topic,
        intents,
        locale,
        generationTime
      })
    })

    return saved.id
  }

  async getGeneration(id: string): Promise<GenerationHistory | null> {
    try {
      return await this.request<GenerationHistory>(`/api/v1/history/${id}`)
    } catch (error) {
      console.warn('Failed to load generation:', id, error)
      return null
    }
  }

  async getAllGenerations(): Promise<GenerationHistory[]> {
    const payload = await this.request<{ generations: GenerationHistory[] }>('/api/v1/history')
    const generations = payload.generations || []
    return generations.sort((a, b) => b.timestamp - a.timestamp)
  }

  async getActiveGeneration(): Promise<GenerationHistory | null> {
    const generations = await this.getAllGenerations()
    return generations.find(g => g.isActive) || null
  }

  async restoreGeneration(id: string): Promise<UpperGraph | null> {
    const payload = await this.request<{ upperGraph: UpperGraph | null }>(`/api/v1/history/${id}/restore`, {
      method: 'POST'
    })
    return payload.upperGraph || null
  }

  async deleteGeneration(id: string): Promise<void> {
    await this.request<{ message: string }>(`/api/v1/history/${id}`, {
      method: 'DELETE'
    })
  }

  async compareGenerations(id1: string, id2: string): Promise<HistoryComparison | null> {
    const [gen1, gen2] = await Promise.all([
      this.getGeneration(id1),
      this.getGeneration(id2)
    ])

    if (!gen1 || !gen2) return null

    const clusters1 = gen1.upperGraph.clusters
    const clusters2 = gen2.upperGraph.clusters

    const addedClusters = clusters2.filter(c2 =>
      !clusters1.some(c1 => c1.cluster_id === c2.cluster_id)
    )

    const removedClusters = clusters1.filter(c1 =>
      !clusters2.some(c2 => c2.cluster_id === c1.cluster_id)
    )

    const modifiedClusters = clusters1
      .filter(c1 => clusters2.some(c2 => c2.cluster_id === c1.cluster_id))
      .map(c1 => {
        const c2 = clusters2.find(c => c.cluster_id === c1.cluster_id)!
        const changes: Record<string, { old: any; new: any }> = {}

        const fieldsToCompare: Array<keyof UpperCluster> = ['name', 'gpt_intent', 'demand_level', 'parent_theme', 'notes']
        fieldsToCompare.forEach(field => {
          if (c1[field] !== c2[field]) {
            changes[field] = {
              old: c1[field],
              new: c2[field]
            }
          }
        })

        return { cluster: c2, changes }
      })
      .filter(item => Object.keys(item.changes).length > 0)

    const metadataChanges: Record<string, { old: any; new: any }> = {}
    Object.keys(gen1.metadata).forEach(key => {
      if (gen1.metadata[key as keyof typeof gen1.metadata] !== gen2.metadata[key as keyof typeof gen2.metadata]) {
        metadataChanges[key] = {
          old: gen1.metadata[key as keyof typeof gen1.metadata],
          new: gen2.metadata[key as keyof typeof gen2.metadata]
        }
      }
    })

    return {
      id1,
      id2,
      differences: {
        addedClusters,
        removedClusters,
        modifiedClusters,
        metadataChanges
      }
    }
  }

  async exportHistory(): Promise<Blob> {
    const generations = await this.getAllGenerations()
    const data = {
      exportDate: new Date().toISOString(),
      version: '2.0',
      generations
    }

    return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  }

  async importHistory(file: File): Promise<number> {
    const text = await file.text()
    const data = JSON.parse(text)

    if (!data.generations || !Array.isArray(data.generations)) {
      throw new Error('Invalid history file format')
    }

    const response = await this.request<{ imported: number }>('/api/v1/history/import', {
      method: 'POST',
      body: JSON.stringify({ generations: data.generations })
    })

    return response.imported || 0
  }
}

export const historyManager = new HistoryManager()
