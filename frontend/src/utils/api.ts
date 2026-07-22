import axios from 'axios'
import type {
  AnalyzeResponse,
  LeadRequest,
  LeadResponse,
  FullReport,
  Lead,
  ReportListItem,
  DashboardStats,
} from './types'

// I produktion: VITE_API_URL pekar på Railway backend
// I utveckling: VITE_API_URL sätts i .env.development till http://localhost:8000
// Backend-origin utan /api — för länkar som renderas direkt i DOM (PDF, widget, rapport)
export const BACKEND_ORIGIN = import.meta.env.VITE_API_URL || ''

const API_BASE_URL = BACKEND_ORIGIN ? `${BACKEND_ORIGIN}/api` : '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const analyzeUrl = async (url: string): Promise<AnalyzeResponse> => {
  const response = await api.post<AnalyzeResponse>('/analyze', { url })
  return response.data
}

export const submitLead = async (data: LeadRequest): Promise<LeadResponse> => {
  const response = await api.post<LeadResponse>('/lead', data)
  return response.data
}

export const getFullReport = async (
  reportId: number,
  token: string
): Promise<FullReport> => {
  const response = await api.get<FullReport>(`/report/${reportId}`, {
    params: { token },
  })
  return response.data
}

// Admin endpoints
export const getLeads = async (
  skip = 0,
  limit = 50
): Promise<Lead[]> => {
  const response = await api.get<Lead[]>('/admin/leads', {
    params: { skip, limit },
  })
  return response.data
}

export const getReports = async (
  skip = 0,
  limit = 50
): Promise<ReportListItem[]> => {
  const response = await api.get<ReportListItem[]>('/admin/reports', {
    params: { skip, limit },
  })
  return response.data
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await api.get<DashboardStats>('/admin/stats')
  return response.data
}

export default api
