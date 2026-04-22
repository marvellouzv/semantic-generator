import axios from 'axios'
import type { 
  UpperGraphRequest, 
  UpperGraph, 
  ExportRequest,
  ClusterTemplate,
  CreateTemplateRequest,
  TemplateListResponse
} from './types'

function resolveApiBaseUrl(): string {
  const raw = String((import.meta as any).env?.VITE_API_URL || '').trim()
  const fallback = 'http://localhost:8000'

  if (!raw) {
    return fallback
  }

  const withProtocol = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`

  try {
    const parsed = new URL(withProtocol)
    return parsed.origin
  } catch (error) {
    console.warn('[API] Invalid VITE_API_URL, fallback to localhost:8000', raw, error)
    return fallback
  }
}
const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 600000,  // 10 РјРёРЅСѓС‚
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const apiService = {
  async generateUpperGraph(data: UpperGraphRequest): Promise<UpperGraph> {
    const response = await api.post<UpperGraph>('/api/v1/upper-graph', data)
    return response.data
  },


  async expandQueries(data: {
    topic: string
    locale: string
    additional_requirements: string
    existing_queries: string[]
    parent_themes: string[]
    allowed_types: string[]
    minus_words?: string[]
    regions?: string[]
  }): Promise<{
    topic: string
    locale: string
    additional_requirements: string
    expanded_queries: Array<{
      query: string
      intent: string
      demand_level: string
      parent_theme: string
      tags: string[]
    }>
  }> {
    const response = await api.post('/api/v1/expand-queries', data)
    return response.data
  },

  async exportData(data: ExportRequest): Promise<Blob> {
    const response = await api.post('/api/v1/export', data, {
      responseType: 'blob'
    })
    return response.data
  },

  async exportClusters(data: { format: 'xlsx' | 'csv', clusters: any[] }): Promise<Blob> {
    const response = await api.post('/api/v1/export-clusters', data, {
      responseType: 'blob'
    })
    return response.data
  },

  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get<{ status: string }>('/health')
    return response.data
  },

  async getProgress(): Promise<{ current: number; total: number; status: string; message: string }> {
    const response = await api.get('/api/v1/progress')
    return response.data
  },

  // ============== TEMPLATES API ==============
  
  async createTemplate(request: CreateTemplateRequest): Promise<ClusterTemplate> {
    const response = await api.post('/api/v1/templates', request)
    return response.data
  },

  async listTemplates(): Promise<TemplateListResponse> {
    const response = await api.get('/api/v1/templates')
    return response.data
  },

  async getTemplate(templateId: string): Promise<ClusterTemplate> {
    const response = await api.get(`/api/v1/templates/${templateId}`)
    return response.data
  },

  async getTemplateAsUpperGraph(templateId: string): Promise<UpperGraph> {
    const response = await api.get(`/api/v1/templates/${templateId}/upper-graph`)
    return response.data
  },

  async deleteTemplate(templateId: string): Promise<{ message: string }> {
    const response = await api.delete(`/api/v1/templates/${templateId}`)
    return response.data
  }
}

export default apiService

