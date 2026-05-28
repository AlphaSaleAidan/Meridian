/**
 * BrandExtractionAgent
 *
 * Scrapes merchant website via SiFt, pulls POS data from Supabase,
 * and uses Claude Sonnet to extract a structured brand voice profile.
 * Saves the result to content_brands.voice_profile.
 */

import Anthropic from '@anthropic-ai/sdk'
import { supabase } from '../../lib/supabase.js'
import { getSiftClient } from '../../lib/sift-scraper.js'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY ?? '' })

export interface BrandVoiceProfile {
  tone: string
  personality: string[]
  targetAudience: string
  uniqueSellingPoints: string[]
  brandValues: string[]
  visualStyle: string
  contentThemes: string[]
  doList: string[]
  dontList: string[]
  samplePhrases: string[]
  industryContext: string
  localContext: string
}

interface MerchantData {
  id: string
  business_name: string
  business_type: string
  website_url?: string
  address?: string
  city?: string
  state?: string
}

/**
 * Extract brand voice from merchant website + POS data.
 */
export async function extractBrandVoice(merchantId: string): Promise<BrandVoiceProfile> {
  if (!supabase) throw new Error('Supabase client not initialized')

  // Pull merchant data from business_accounts
  const { data: merchant, error: merchantErr } = await supabase
    .from('business_accounts')
    .select('id, business_name, business_type, website_url, address, city, state')
    .eq('id', merchantId)
    .single()

  if (merchantErr || !merchant) {
    throw new Error(`Merchant ${merchantId} not found: ${merchantErr?.message}`)
  }

  const merchantData = merchant as MerchantData

  // Pull existing brand row if any
  const { data: brand } = await supabase
    .from('content_brands')
    .select('website_url')
    .eq('merchant_id', merchantId)
    .single()

  const websiteUrl = brand?.website_url ?? merchantData.website_url

  // Scrape website via SiFt
  let websiteContent = ''
  if (websiteUrl) {
    const sift = getSiftClient()
    if (sift) {
      try {
        const result = await sift.scrape(websiteUrl, {
          strategy: 'markdown',
          maxPages: 3,
          followLinks: true,
        })
        websiteContent = result.markdown.slice(0, 8000)
      } catch (err) {
        console.warn(`[brand-extraction] SiFt scrape failed for ${websiteUrl}:`, err)
      }
    }
  }

  // Pull recent POS data for context (top products, categories)
  let posContext = ''
  try {
    const { data: posItems } = await supabase
      .from('pos_items')
      .select('name, category, total_revenue')
      .eq('org_id', merchantId)
      .order('total_revenue', { ascending: false })
      .limit(20)

    if (posItems && posItems.length > 0) {
      const lines = posItems.map(
        (p: { name: string; category: string; total_revenue: number }) =>
          `- ${p.name} (${p.category}): $${(p.total_revenue / 100).toFixed(2)} revenue`
      )
      posContext = `Top products:\n${lines.join('\n')}`
    }
  } catch {
    // POS data is optional
  }

  // Use Claude Sonnet to extract brand voice
  const systemPrompt = `You are a brand strategist analyzing a local business. Extract a structured brand voice profile from the provided data. Return valid JSON matching the schema exactly.`

  const userPrompt = `Analyze this business and create a brand voice profile:

Business: ${merchantData.business_name}
Type: ${merchantData.business_type}
Location: ${merchantData.city ?? ''}, ${merchantData.state ?? ''}

${websiteContent ? `Website content:\n${websiteContent}\n` : 'No website content available.\n'}
${posContext ? `\n${posContext}\n` : ''}

Return a JSON object with these exact keys:
{
  "tone": "one-word primary tone (e.g. friendly, professional, edgy)",
  "personality": ["array of 3-5 brand personality traits"],
  "targetAudience": "primary audience description",
  "uniqueSellingPoints": ["3-5 USPs"],
  "brandValues": ["3-5 core values"],
  "visualStyle": "description of visual style for content",
  "contentThemes": ["5-7 recurring content themes"],
  "doList": ["5 things to always do in content"],
  "dontList": ["5 things to never do in content"],
  "samplePhrases": ["5 on-brand example phrases"],
  "industryContext": "industry-specific context for content",
  "localContext": "local/regional context for content"
}`

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 2048,
    messages: [{ role: 'user', content: userPrompt }],
    system: systemPrompt,
  })

  const textBlock = response.content.find((b) => b.type === 'text')
  if (!textBlock || textBlock.type !== 'text') {
    throw new Error('Claude returned no text response')
  }

  // Extract JSON from response (handles markdown code blocks)
  let jsonStr = textBlock.text
  const jsonMatch = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (jsonMatch) {
    jsonStr = jsonMatch[1]
  }

  const profile: BrandVoiceProfile = JSON.parse(jsonStr.trim())

  // Save to content_brands
  const { error: upsertErr } = await supabase
    .from('content_brands')
    .update({
      voice_profile: profile,
      updated_at: new Date().toISOString(),
    })
    .eq('merchant_id', merchantId)

  if (upsertErr) {
    console.error(`[brand-extraction] Failed to save voice profile:`, upsertErr)
    throw upsertErr
  }

  return profile
}
