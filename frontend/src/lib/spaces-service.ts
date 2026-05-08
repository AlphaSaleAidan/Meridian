import { supabase } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface Space {
  id: string
  org_id: string
  name: string
  scan_type: string
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  pointcloud_url: string | null
  thumbnail_url: string | null
  frame_count: number | null
  scan_duration_seconds: number | null
  model_used: string | null
  zones_configured: boolean
  heatmap_enabled: boolean
  created_at: string
  completed_at: string | null
  error_message: string | null
}

export interface ProcessingJob {
  id: string
  space_id: string | null
  status: 'queued' | 'processing' | 'complete' | 'failed'
  progress_pct: number
  frame_count: number | null
  error_message: string | null
  created_at: string
}

export interface ZoneDefinition {
  id?: string
  space_id: string
  zone_name: string
  zone_type: string
  color: string
  polygon_coords: number[][]
}

const SPACES_STORAGE_KEY = 'meridian_spaces'
const JOBS_STORAGE_KEY = 'meridian_space_jobs'

function loadLocalSpaces(): Space[] {
  try {
    const raw = localStorage.getItem(SPACES_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveLocalSpaces(spaces: Space[]) {
  localStorage.setItem(SPACES_STORAGE_KEY, JSON.stringify(spaces))
}

function loadLocalJobs(): ProcessingJob[] {
  try {
    const raw = localStorage.getItem(JOBS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveLocalJobs(jobs: ProcessingJob[]) {
  localStorage.setItem(JOBS_STORAGE_KEY, JSON.stringify(jobs))
}

export const spacesService = {
  async list(orgId: string): Promise<Space[]> {
    if (supabase) {
      const { data } = await supabase
        .from('spaces')
        .select('*')
        .eq('org_id', orgId)
        .order('created_at', { ascending: false })
      if (data) return data as Space[]
    }
    return loadLocalSpaces().filter(s => s.org_id === orgId)
  },

  async getById(spaceId: string): Promise<Space | null> {
    if (supabase) {
      const { data } = await supabase
        .from('spaces')
        .select('*')
        .eq('id', spaceId)
        .single()
      if (data) return data as Space
    }
    return loadLocalSpaces().find(s => s.id === spaceId) ?? null
  },

  async uploadVideo(orgId: string, scanName: string, file: File): Promise<{ jobId: string; spaceId: string }> {
    if (API_BASE) {
      const formData = new FormData()
      formData.append('video', file)
      formData.append('merchant_id', orgId)
      formData.append('scan_name', scanName)
      const res = await fetch(`${API_BASE}/api/spaces/process`, { method: 'POST', body: formData })
      if (res.ok) return res.json()
    }

    const spaceId = crypto.randomUUID()
    const jobId = crypto.randomUUID()
    const now = new Date().toISOString()

    const space: Space = {
      id: spaceId,
      org_id: orgId,
      name: scanName,
      scan_type: 'lingbot',
      status: 'processing',
      pointcloud_url: null,
      thumbnail_url: null,
      frame_count: null,
      scan_duration_seconds: null,
      model_used: null,
      zones_configured: false,
      heatmap_enabled: false,
      created_at: now,
      completed_at: null,
      error_message: null,
    }

    const job: ProcessingJob = {
      id: jobId,
      space_id: spaceId,
      status: 'processing',
      progress_pct: 0,
      frame_count: null,
      error_message: null,
      created_at: now,
    }

    const spaces = loadLocalSpaces()
    spaces.unshift(space)
    saveLocalSpaces(spaces)

    const jobs = loadLocalJobs()
    jobs.unshift(job)
    saveLocalJobs(jobs)

    simulateProcessing(jobId, spaceId)

    return { jobId, spaceId }
  },

  async getJobStatus(jobId: string): Promise<ProcessingJob | null> {
    if (API_BASE) {
      const res = await fetch(`${API_BASE}/api/spaces/jobs/${jobId}`)
      if (res.ok) return res.json()
    }
    return loadLocalJobs().find(j => j.id === jobId) ?? null
  },

  async getZones(spaceId: string): Promise<ZoneDefinition[]> {
    if (supabase) {
      const { data } = await supabase
        .from('space_zones')
        .select('*')
        .eq('space_id', spaceId)
      if (data) return data as ZoneDefinition[]
    }
    return []
  },

  async saveZone(zone: ZoneDefinition): Promise<void> {
    if (supabase) {
      await supabase.from('space_zones').insert({
        id: crypto.randomUUID(),
        space_id: zone.space_id,
        zone_id: zone.zone_name.toLowerCase().replace(/\s+/g, '-'),
        label: zone.zone_name,
        category: zone.zone_type,
      })
    }
  },

  async deleteSpace(spaceId: string): Promise<void> {
    if (supabase) {
      await supabase.from('spaces').delete().eq('id', spaceId)
    }
    const spaces = loadLocalSpaces().filter(s => s.id !== spaceId)
    saveLocalSpaces(spaces)
  },
}

function simulateProcessing(jobId: string, spaceId: string) {
  const stages = [
    { pct: 10, delay: 1500 },
    { pct: 20, delay: 2000 },
    { pct: 45, delay: 3000 },
    { pct: 65, delay: 3000 },
    { pct: 80, delay: 2500 },
    { pct: 95, delay: 2000 },
    { pct: 100, delay: 1500 },
  ]

  let i = 0
  function tick() {
    if (i >= stages.length) return
    const stage = stages[i]
    setTimeout(() => {
      const jobs = loadLocalJobs()
      const job = jobs.find(j => j.id === jobId)
      if (job) {
        job.progress_pct = stage.pct
        if (stage.pct >= 100) {
          job.status = 'complete'
          job.frame_count = 1847

          const spaces = loadLocalSpaces()
          const space = spaces.find(s => s.id === spaceId)
          if (space) {
            space.status = 'ready'
            space.frame_count = 1847
            space.scan_duration_seconds = 184
            space.model_used = 'lingbot-map.pt'
            space.completed_at = new Date().toISOString()
            saveLocalSpaces(spaces)
          }
        }
        saveLocalJobs(jobs)
      }
      i++
      tick()
    }, stage.delay)
  }
  tick()
}
