/**
 * SEOAgent
 *
 * - discoverKeywords(): DataForSEO keyword research with seed generation
 * - checkRankings(): DataForSEO SERP rank check, saves snapshots to content_rankings
 */

import Anthropic from '@anthropic-ai/sdk'
import {
  keywordResearch,
  postRankCheckTasks,
  fetchRankCheckResults,
} from '../../lib/dataforseo.js'
import { supabase } from '../../lib/supabase.js'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY ?? '' })

// ── Keyword Discovery ───────────────────────────────────────────────────────

export interface KeywordDiscoveryInput {
  merchantId: string
  businessType: string
  businessName: string
  city?: string
  state?: string
  existingKeywords?: string[]
}

export interface DiscoveredKeyword {
  keyword: string
  searchVolume: number
  competition: number
  cpc: number
  difficulty: number
}

export async function discoverKeywords(
  input: KeywordDiscoveryInput
): Promise<DiscoveredKeyword[]> {
  // Generate seed keywords using Claude Haiku
  const seedPrompt = `Generate 10 high-intent seed keywords for a ${input.businessType} named "${input.businessName}" in ${input.city ?? 'a local area'}, ${input.state ?? 'US'}.

Focus on:
- Local service keywords ("best [type] near me", "[city] [type]")
- Product/menu keywords
- Problem-solving keywords ("how to...", "where to...")
- Competitor comparison keywords

${input.existingKeywords?.length ? `Already tracking: ${input.existingKeywords.join(', ')}. Find NEW ones.` : ''}

Return a JSON array of strings, nothing else.`

  const response = await anthropic.messages.create({
    model: 'claude-haiku-4-20250514',
    max_tokens: 512,
    messages: [{ role: 'user', content: seedPrompt }],
  })

  const textBlock = response.content.find((b) => b.type === 'text')
  if (!textBlock || textBlock.type !== 'text') {
    throw new Error('Claude returned no seed keywords')
  }

  let seedKeywords: string[]
  try {
    let jsonStr = textBlock.text
    const match = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
    if (match) jsonStr = match[1]
    seedKeywords = JSON.parse(jsonStr.trim()) as string[]
  } catch {
    // Fallback: extract quoted strings
    seedKeywords = (textBlock.text.match(/"([^"]+)"/g) ?? []).map((s) =>
      s.replace(/"/g, '')
    )
  }

  if (seedKeywords.length === 0) {
    seedKeywords = [
      `${input.businessType} ${input.city ?? ''}`.trim(),
      `best ${input.businessType} near me`,
    ]
  }

  // Run DataForSEO keyword research
  const results = await keywordResearch({
    seedKeywords,
    limit: 50,
  })

  // Sort by search volume (descending), filter out low-value
  return results
    .filter((k) => k.searchVolume > 10)
    .sort((a, b) => b.searchVolume - a.searchVolume)
    .slice(0, 30)
}

// ── Rank Checking ───────────────────────────────────────────────────────────

export interface RankCheckInput {
  merchantId: string
  keywords: string[]
  targetDomain: string
  locationCode?: number
}

export interface RankSnapshot {
  keyword: string
  rankPosition: number | null
  rankAbsolute: number | null
  urlRanked: string | null
  serpFeatures: string[]
  rankChange: number
}

export async function checkRankings(
  input: RankCheckInput
): Promise<RankSnapshot[]> {
  if (!supabase) throw new Error('Supabase client not initialized')

  // Post rank check tasks to DataForSEO
  const taskIds = await postRankCheckTasks({
    keywords: input.keywords,
    targetDomain: input.targetDomain,
    locationCode: input.locationCode,
  })

  if (taskIds.length === 0) {
    console.warn('[seo-agent] No rank check tasks created')
    return []
  }

  // Wait for tasks to process (DataForSEO typically takes 30-60s)
  await sleep(45_000)

  // Fetch results
  const results = await fetchRankCheckResults(taskIds)

  // Get previous rankings for rank change calculation
  const snapshots: RankSnapshot[] = []

  for (const result of results) {
    let rankChange = 0

    // Look up previous rank for this keyword
    const { data: prevRank } = await supabase
      .from('content_rankings')
      .select('rank_position')
      .eq('merchant_id', input.merchantId)
      .eq('keyword', result.keyword)
      .order('checked_at', { ascending: false })
      .limit(1)
      .single()

    if (prevRank?.rank_position && result.rankPosition) {
      rankChange = prevRank.rank_position - result.rankPosition
    }

    const snapshot: RankSnapshot = {
      keyword: result.keyword,
      rankPosition: result.rankPosition,
      rankAbsolute: result.rankAbsolute,
      urlRanked: result.urlRanked,
      serpFeatures: result.serpFeatures,
      rankChange,
    }

    // Save to content_rankings
    const { error } = await supabase.from('content_rankings').insert({
      merchant_id: input.merchantId,
      keyword: result.keyword,
      rank_position: result.rankPosition,
      rank_absolute: result.rankAbsolute,
      url_ranked: result.urlRanked,
      serp_features: result.serpFeatures,
      rank_change: rankChange,
    })

    if (error) {
      console.error(
        `[seo-agent] Failed to save ranking for "${result.keyword}":`,
        error
      )
    }

    snapshots.push(snapshot)
  }

  return snapshots
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
