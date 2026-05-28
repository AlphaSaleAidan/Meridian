/**
 * Ayrshare API client with per-merchant profile management.
 * Uses AYRSHARE_API_KEY for primary auth, profileKey for merchant-specific ops.
 */

const BASE_URL = 'https://app.ayrshare.com/api'

function getApiKey(): string {
  return process.env.AYRSHARE_API_KEY ?? ''
}

async function ayrshareRequest<T>(
  path: string,
  options: {
    method?: string
    body?: unknown
    profileKey?: string
  } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getApiKey()}`,
  }

  if (options.profileKey) {
    headers['Profile-Key'] = options.profileKey
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'POST',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Ayrshare ${path} failed (${response.status}): ${text}`)
  }

  return response.json() as Promise<T>
}

export interface AyrshareProfile {
  profileKey: string
  title: string
}

/**
 * Create a new Ayrshare sub-profile for a merchant.
 */
export async function createAyrshareProfile(params: {
  title: string
}): Promise<AyrshareProfile> {
  const data = await ayrshareRequest<{
    profileKey?: string
    title?: string
  }>('/profiles/profile', {
    body: { title: params.title },
  })

  return {
    profileKey: data.profileKey ?? '',
    title: data.title ?? params.title,
  }
}

export interface PublishPostParams {
  profileKey: string
  post: string
  platforms: string[]
  mediaUrls?: string[]
  scheduledDate?: string
  title?: string
}

export interface PublishPostResult {
  id: string
  postIds: Record<string, string>
  status: string
}

/**
 * Publish a post to social platforms via a merchant's profile.
 */
export async function publishPost(
  params: PublishPostParams
): Promise<PublishPostResult> {
  const body: Record<string, unknown> = {
    post: params.post,
    platforms: params.platforms,
  }

  if (params.mediaUrls && params.mediaUrls.length > 0) {
    body.mediaUrls = params.mediaUrls
  }
  if (params.scheduledDate) {
    body.scheduleDate = params.scheduledDate
  }
  if (params.title) {
    body.title = params.title
  }

  const data = await ayrshareRequest<{
    id?: string
    postIds?: Record<string, string>
    status?: string
  }>('/post', {
    body,
    profileKey: params.profileKey,
  })

  return {
    id: data.id ?? '',
    postIds: data.postIds ?? {},
    status: data.status ?? 'success',
  }
}

/**
 * Get the platform-connect URL so a merchant can link their social accounts.
 */
export async function getPlatformConnectUrl(params: {
  profileKey: string
}): Promise<string> {
  const data = await ayrshareRequest<{ url?: string }>(
    '/profiles/generateJWT',
    {
      body: { domain: 'meridian.tips' },
      profileKey: params.profileKey,
    }
  )

  return data.url ?? ''
}
