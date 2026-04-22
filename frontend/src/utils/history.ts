import type { UpperGraph, UpperCluster } from '../types'

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
  private dbName = 'SemanticGeneratorHistory'
  private dbVersion = 1
  private db: IDBDatabase | null = null
  private maxHistoryItems = 50

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)
      
      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result
        
        // Создаем store для истории генераций
        if (!db.objectStoreNames.contains('generations')) {
          const store = db.createObjectStore('generations', { keyPath: 'id' })
          store.createIndex('timestamp', 'timestamp', { unique: false })
          store.createIndex('topic', 'topic', { unique: false })
          store.createIndex('isActive', 'isActive', { unique: false })
        }
        
        // Создаем store для сравнений
        if (!db.objectStoreNames.contains('comparisons')) {
          const store = db.createObjectStore('comparisons', { keyPath: 'id' })
          store.createIndex('timestamp', 'timestamp', { unique: false })
        }
      }
    })
  }

  async saveGeneration(upperGraph: UpperGraph, topic: string, intents: string[], locale: string, generationTime: number): Promise<string> {
    if (!this.db) await this.init()

    const id = `gen_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    // Деактивируем все предыдущие генерации
    await this.deactivateAllGenerations()
    
    const historyItem: GenerationHistory = {
      id,
      timestamp: Date.now(),
      topic,
      intents,
      locale,
      upperGraph,
      metadata: {
        generationTime,
        clusterCount: upperGraph.clusters.length,
        highDemandCount: upperGraph.clusters.filter(c => c.demand_level === 'High').length,
        commercialCount: upperGraph.clusters.filter(c => c.gpt_intent === 'commercial').length,
        parentThemes: [...new Set(upperGraph.clusters.map(c => c.parent_theme).filter(Boolean))] as string[]
      },
      version: 1,
      isActive: true
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readwrite')
      const store = transaction.objectStore('generations')
      const request = store.add(historyItem)
      
      request.onsuccess = () => {
        this.cleanupOldHistory()
        resolve(id)
      }
      request.onerror = () => reject(request.error)
    })
  }

  async getGeneration(id: string): Promise<GenerationHistory | null> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readonly')
      const store = transaction.objectStore('generations')
      const request = store.get(id)
      
      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  async getAllGenerations(): Promise<GenerationHistory[]> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readonly')
      const store = transaction.objectStore('generations')
      const index = store.index('timestamp')
      const request = index.getAll()
      
      request.onsuccess = () => {
        const results = request.result || []
        // Сортируем по timestamp (новые сначала)
        results.sort((a, b) => b.timestamp - a.timestamp)
        resolve(results)
      }
      request.onerror = () => reject(request.error)
    })
  }

  async getActiveGeneration(): Promise<GenerationHistory | null> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readonly')
      const store = transaction.objectStore('generations')
      const index = store.index('isActive')
      const request = index.get(true)
      
      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  async restoreGeneration(id: string): Promise<UpperGraph | null> {
    const history = await this.getGeneration(id)
    if (!history) return null

    // Деактивируем все генерации и активируем выбранную
    await this.deactivateAllGenerations()
    await this.activateGeneration(id)

    return history.upperGraph
  }

  async deleteGeneration(id: string): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readwrite')
      const store = transaction.objectStore('generations')
      const request = store.delete(id)
      
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
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

    // Находим добавленные кластеры
    const addedClusters = clusters2.filter(c2 => 
      !clusters1.some(c1 => c1.cluster_id === c2.cluster_id)
    )

    // Находим удаленные кластеры
    const removedClusters = clusters1.filter(c1 => 
      !clusters2.some(c2 => c2.cluster_id === c1.cluster_id)
    )

    // Находим измененные кластеры
    const modifiedClusters = clusters1
      .filter(c1 => clusters2.some(c2 => c2.cluster_id === c1.cluster_id))
      .map(c1 => {
        const c2 = clusters2.find(c => c.cluster_id === c1.cluster_id)!
        const changes: Record<string, { old: any; new: any }> = {}
        
        // Сравниваем поля
        const fieldsToCompare = ['name', 'gpt_intent', 'demand_level', 'parent_theme', 'tags', 'notes']
        fieldsToCompare.forEach(field => {
          if (c1[field as keyof UpperCluster] !== c2[field as keyof UpperCluster]) {
            changes[field] = {
              old: c1[field as keyof UpperCluster],
              new: c2[field as keyof UpperCluster]
            }
          }
        })

        return { cluster: c2, changes }
      })
      .filter(item => Object.keys(item.changes).length > 0)

    // Сравниваем метаданные
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
      version: '1.0',
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

    let importedCount = 0
    for (const generation of data.generations) {
      try {
        await this.saveGeneration(
          generation.upperGraph,
          generation.topic,
          generation.intents,
          generation.locale,
          generation.metadata.generationTime
        )
        importedCount++
      } catch (error) {
        console.warn('Failed to import generation:', generation.id, error)
      }
    }

    return importedCount
  }

  private async deactivateAllGenerations(): Promise<void> {
    if (!this.db) return

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readwrite')
      const store = transaction.objectStore('generations')
      const index = store.index('isActive')
      const request = index.getAll()

      request.onsuccess = () => {
        const activeGenerations = request.result || []
        const updatePromises = activeGenerations.map(gen => {
          const updateTransaction = this.db!.transaction(['generations'], 'readwrite')
          const updateStore = updateTransaction.objectStore('generations')
          gen.isActive = false
          return updateStore.put(gen)
        })

        Promise.all(updatePromises).then(() => resolve()).catch(reject)
      }
      request.onerror = () => reject(request.error)
    })
  }

  private async activateGeneration(id: string): Promise<void> {
    if (!this.db) return

    const generation = await this.getGeneration(id)
    if (!generation) return

    generation.isActive = true

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['generations'], 'readwrite')
      const store = transaction.objectStore('generations')
      const request = store.put(generation)
      
      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  private async cleanupOldHistory(): Promise<void> {
    if (!this.db) return

    const allGenerations = await this.getAllGenerations()
    if (allGenerations.length <= this.maxHistoryItems) return

    // Удаляем самые старые генерации
    const toDelete = allGenerations
      .filter(gen => !gen.isActive)
      .sort((a, b) => a.timestamp - b.timestamp)
      .slice(0, allGenerations.length - this.maxHistoryItems)

    for (const gen of toDelete) {
      await this.deleteGeneration(gen.id)
    }
  }
}

export const historyManager = new HistoryManager()
