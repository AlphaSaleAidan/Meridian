/**
 * Content API Client
 *
 * Mirrors the pattern in @/lib/api.ts:
 * - Demo mode returns mock data via fetchDemoContentData()
 * - Real mode calls apiFetch() against /api/content/* endpoints
 */

import { fetchDemoContentData, type ContentDashboardData } from './content-demo-data'
import { getAuthHeaders } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

function isDemo(orgId: string): boolean {
  return orgId === 'demo'
}

function delay<T>(data: T, ms = 400): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(data), ms + Math.random() * 200))
}

interface ApiFetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: Record<string, unknown>
}

async function apiFetch<T>(path: string, opts?: ApiFetchOptions): Promise<T> {
  const url = `${API_BASE}${path}`
  const authHeaders = await getAuthHeaders()

  const fetchOpts: RequestInit = {
    method: opts?.method || 'GET',
    credentials: 'include',
    headers: { ...authHeaders, Accept: 'application/json' },
  }

  if (opts?.body) {
    fetchOpts.headers = {
      ...fetchOpts.headers,
      'Content-Type': 'application/json',
    }
    fetchOpts.body = JSON.stringify(opts.body)
  }

  const res = await fetch(url, fetchOpts)

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }

  return res.json()
}

export const contentApi = {
  dashboard: (orgId: string): Promise<ContentDashboardData> =>
    isDemo(orgId)
      ? delay(fetchDemoContentData())
      : apiFetch<ContentDashboardData>('/api/content/dashboard/' + orgId),

  approvePost: (postId: string, merchantId: string, scheduledAt?: string) =>
    apiFetch<{ ok: boolean }>('/api/content/posts/' + postId + '/approve', {
      method: 'PATCH',
      body: { merchantId, scheduledAt },
    }),

  rejectPost: (postId: string) =>
    apiFetch<{ ok: boolean }>('/api/content/posts/' + postId + '/reject', {
      method: 'PATCH',
    }),

  regeneratePost: (postId: string, field: string, merchantId: string) =>
    apiFetch<{ ok: boolean }>('/api/content/posts/' + postId + '/regenerate', {
      method: 'POST',
      body: { merchantId, field },
    }),

  generateCalendar: (merchantId: string) =>
    apiFetch<{ ok: boolean; jobIds: string[] }>('/api/content/calendar/generate/' + merchantId, {
      method: 'POST',
    }),

  generateVideo: (merchantId: string, params: {
    prompt: string
    platform: string
    model?: string
    style?: string
    durationSeconds?: number
    brand?: { business_name: string; business_type: string; voice_profile?: Record<string, unknown> }
    enhance?: boolean
  }) =>
    apiFetch<{
      ok: boolean
      jobId?: string
      videoUrl?: string
      model?: string
      status?: string
      director?: { style_notes: string; model_recommendation: string; original_prompt: string }
    }>('/api/content/video/generate', {
      method: 'POST',
      body: { merchantId, ...params },
    }),

  generateImage: (merchantId: string, params: {
    prompt: string
    platform?: string
    width?: number
    height?: number
    style?: string
    brand?: { business_name: string; business_type: string; voice_profile?: Record<string, unknown> }
    enhance?: boolean
  }) =>
    apiFetch<{
      ok: boolean
      imageUrl?: string
      seed?: number
      director?: { style_notes: string; model_recommendation: string; original_prompt: string }
    }>('/api/content/image/generate', {
      method: 'POST',
      body: { merchantId, ...params },
    }),

  directorPreview: (merchantId: string, params: {
    prompt: string
    platform?: string
    style?: string
    media_type?: string
    durationSeconds?: number
    brand: { business_name: string; business_type: string; voice_profile?: Record<string, unknown> }
  }) =>
    apiFetch<{
      ok: boolean
      enhanced_prompt: string
      original_prompt: string
      generation_config: Record<string, unknown>
      style_notes: string
      model_recommendation: string
    }>('/api/content/director/preview', {
      method: 'POST',
      body: { merchantId, ...params },
    }),

  directorStyles: () =>
    apiFetch<{
      styles: Record<string, string>
      platforms: Record<string, unknown>
      business_types: Record<string, unknown>
    }>('/api/content/director/styles'),

  videoStatus: (jobId: string) =>
    apiFetch<{
      jobId: string
      status: 'processing' | 'completed' | 'failed'
      videoUrl?: string
      error?: string
      model?: string
      fal_status?: string
      elapsed?: number
      ok?: boolean
      director?: { style_notes: string; model_recommendation: string; original_prompt: string }
      enhanced_prompt?: string
    }>(`/api/content/video/status/${jobId}`),

  scrapeWebsite: (merchantId: string, url: string) =>
    apiFetch<{
      ok: boolean
      domain: string
      title: string
      meta_description: string
      meta_keywords: string
      logos: string[]
      headings: { level: string; text: string }[]
      social_links: Record<string, string>
      brand_colors: string[]
      content_preview: string
      word_count: number
    }>('/api/content/scrape/website', {
      method: 'POST',
      body: { merchantId, url },
    }),

  generatePost: (merchantId: string, params: {
    prompt: string
    platform?: string
    postType?: string
    referenceImageUrl?: string
    brand?: { business_name: string; business_type: string; voice_profile?: Record<string, unknown> }
    websiteContext?: string
  }) =>
    apiFetch<{
      ok: boolean
      post: {
        hook: string
        body: string
        hashtags: string[]
        call_to_action: string
        suggested_image_prompt?: string
      }
      platform: string
    }>('/api/content/post/generate', {
      method: 'POST',
      body: { merchantId, ...params },
    }),

  generateSeo: (merchantId: string, params: {
    targetKeyword: string
    websiteUrl?: string
    contentType?: string
    wordCount?: number
    websiteContext?: string
  }) =>
    apiFetch<{
      ok: boolean
      seo_content: {
        meta_title: string
        meta_description: string
        content_html: string
        word_count: number
        keyword_density: number
        headers: string[]
        internal_links: string[]
        schema_suggestion: string
      }
      target_keyword: string
      content_type: string
    }>('/api/content/seo/generate', {
      method: 'POST',
      body: { merchantId, ...params },
    }),
}
