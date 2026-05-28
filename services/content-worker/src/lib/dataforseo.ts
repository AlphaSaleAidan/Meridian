/**
 * DataForSEO API client.
 * Basic auth from DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD.
 */

const BASE_URL = 'https://api.dataforseo.com/v3'

function getAuthHeader(): string {
  const login = process.env.DATAFORSEO_LOGIN ?? ''
  const password = process.env.DATAFORSEO_PASSWORD ?? ''
  return 'Basic ' + Buffer.from(`${login}:${password}`).toString('base64')
}

async function apiRequest<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': getAuthHeader(),
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`DataForSEO ${path} failed (${response.status}): ${text}`)
  }

  return response.json() as Promise<T>
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers: {
      'Authorization': getAuthHeader(),
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`DataForSEO GET ${path} failed (${response.status}): ${text}`)
  }

  return response.json() as Promise<T>
}

export interface KeywordResult {
  keyword: string
  searchVolume: number
  competition: number
  cpc: number
  difficulty: number
}

interface DataForSEOResponse {
  tasks?: Array<{
    id?: string
    result?: Array<{
      items?: Array<{
        keyword?: string
        keyword_data?: {
          keyword?: string
          search_volume?: number
          competition?: number
          cpc?: number
          keyword_difficulty?: number
        }
        search_volume?: number
        competition?: number
        cpc?: number
        keyword_difficulty?: number
      }>
    }>
  }>
}

interface RankTaskResponse {
  tasks?: Array<{
    id?: string
    status_code?: number
  }>
}

interface RankResultItem {
  type?: string
  rank_group?: number
  rank_absolute?: number
  url?: string
  se_type?: string
}

interface RankResultResponse {
  tasks?: Array<{
    result?: Array<{
      keyword?: string
      items?: RankResultItem[]
    }>
  }>
}

/**
 * Keyword research: discover keywords related to seed terms.
 */
export async function keywordResearch(params: {
  seedKeywords: string[]
  locationCode?: number
  languageCode?: string
  limit?: number
}): Promise<KeywordResult[]> {
  const payload = [
    {
      keywords: params.seedKeywords,
      location_code: params.locationCode ?? 2840,
      language_code: params.languageCode ?? 'en',
      include_seed_keyword: true,
      limit: params.limit ?? 50,
    },
  ]

  const data = await apiRequest<DataForSEOResponse>(
    '/keywords_data/google_ads/keywords_for_keywords/live',
    payload
  )

  const items = data.tasks?.[0]?.result?.[0]?.items ?? []

  return items.map((item) => ({
    keyword: item.keyword ?? item.keyword_data?.keyword ?? '',
    searchVolume:
      item.search_volume ?? item.keyword_data?.search_volume ?? 0,
    competition:
      item.competition ?? item.keyword_data?.competition ?? 0,
    cpc: item.cpc ?? item.keyword_data?.cpc ?? 0,
    difficulty:
      item.keyword_difficulty ?? item.keyword_data?.keyword_difficulty ?? 0,
  }))
}

/**
 * Post SERP rank-check tasks (async). Returns task IDs.
 */
export async function postRankCheckTasks(params: {
  keywords: string[]
  targetDomain: string
  locationCode?: number
  languageCode?: string
}): Promise<string[]> {
  const tasks = params.keywords.map((keyword) => ({
    keyword,
    url: params.targetDomain,
    location_code: params.locationCode ?? 2840,
    language_code: params.languageCode ?? 'en',
    device: 'desktop',
    os: 'windows',
    depth: 100,
  }))

  const data = await apiRequest<RankTaskResponse>(
    '/serp/google/organic/task_post',
    tasks
  )

  return (data.tasks ?? [])
    .filter((t) => t.status_code === 20100 && t.id)
    .map((t) => t.id!)
}

/**
 * Fetch rank check results for completed tasks.
 */
export async function fetchRankCheckResults(taskIds: string[]): Promise<
  Array<{
    keyword: string
    rankPosition: number | null
    rankAbsolute: number | null
    urlRanked: string | null
    serpFeatures: string[]
  }>
> {
  const results: Array<{
    keyword: string
    rankPosition: number | null
    rankAbsolute: number | null
    urlRanked: string | null
    serpFeatures: string[]
  }> = []

  for (const taskId of taskIds) {
    try {
      const data = await apiGet<RankResultResponse>(
        `/serp/google/organic/task_get/regular/${taskId}`
      )

      const taskResult = data.tasks?.[0]?.result?.[0]
      if (!taskResult) continue

      const items = taskResult.items ?? []
      const firstOrganic = items.find((i) => i.type === 'organic')
      const features = items
        .filter((i) => i.type && i.type !== 'organic')
        .map((i) => i.type!)

      results.push({
        keyword: taskResult.keyword ?? '',
        rankPosition: firstOrganic?.rank_group ?? null,
        rankAbsolute: firstOrganic?.rank_absolute ?? null,
        urlRanked: firstOrganic?.url ?? null,
        serpFeatures: features,
      })
    } catch (err) {
      console.error(`[dataforseo] Failed to fetch task ${taskId}:`, err)
    }
  }

  return results
}
