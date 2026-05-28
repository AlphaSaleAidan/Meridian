/**
 * Thin HTTP bridge to SiFt scraper service.
 * Uses SIFT_SCRAPER_ENDPOINT and SIFT_SCRAPER_API_KEY.
 */

export interface SiftScrapeOptions {
  strategy: 'markdown' | 'html' | 'text'
  maxPages?: number
  followLinks?: boolean
}

export interface SiftScrapeResult {
  markdown: string
  title?: string
  links?: string[]
}

class SiftClient {
  private endpoint: string
  private apiKey: string

  constructor(endpoint: string, apiKey: string) {
    this.endpoint = endpoint.replace(/\/+$/, '')
    this.apiKey = apiKey
  }

  async scrape(url: string, options: SiftScrapeOptions): Promise<SiftScrapeResult> {
    const response = await fetch(`${this.endpoint}/scrape`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        url,
        strategy: options.strategy,
        max_pages: options.maxPages ?? 1,
        follow_links: options.followLinks ?? false,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`SiFt scrape failed (${response.status}): ${text}`)
    }

    const data = await response.json() as Record<string, unknown>

    return {
      markdown: (data.markdown as string) ?? (data.content as string) ?? '',
      title: (data.title as string) ?? undefined,
      links: (data.links as string[]) ?? undefined,
    }
  }
}

let _client: SiftClient | null = null

export function getSiftClient(): SiftClient | null {
  if (_client) return _client

  const endpoint = process.env.SIFT_SCRAPER_ENDPOINT
  const apiKey = process.env.SIFT_SCRAPER_API_KEY

  if (!endpoint || !apiKey) {
    console.warn('[sift-scraper] SIFT_SCRAPER_ENDPOINT or SIFT_SCRAPER_API_KEY not set')
    return null
  }

  _client = new SiftClient(endpoint, apiKey)
  return _client
}
