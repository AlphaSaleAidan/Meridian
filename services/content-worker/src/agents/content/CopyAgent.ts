/**
 * CopyAgent
 *
 * - generateSocialPost(): Claude Haiku for platform-specific social copy
 * - generateSEOArticle(): DeepSeek V3 for starter/growth, Claude Sonnet for command tier
 *
 * Both return structured JSON.
 */

import Anthropic from '@anthropic-ai/sdk'
import { deepseekClient, DEEPSEEK_MODEL } from '../../lib/deepseek.js'
import { supabase } from '../../lib/supabase.js'
import type { BrandVoiceProfile } from './BrandExtractionAgent.js'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY ?? '' })

// ── Platform-specific rules ─────────────────────────────────────────────────

const PLATFORM_RULES: Record<string, string> = {
  instagram: `Instagram rules:
- Max 2200 chars, but keep under 300 for feed posts
- Use 5-15 relevant hashtags at the end
- Start with a hook (question, bold statement, or emoji)
- Include a clear CTA
- Use line breaks for readability`,

  facebook: `Facebook rules:
- 1-3 paragraphs, conversational tone
- Include a question to drive engagement
- Hashtags: 1-3 max
- CTA that encourages comments/shares`,

  twitter: `Twitter/X rules:
- Max 280 chars
- Punchy and direct
- 1-2 hashtags max
- Thread-worthy content can be split`,

  linkedin: `LinkedIn rules:
- Professional but personable
- Start with a hook line
- Use line breaks and white space
- 3-5 hashtags
- 1300 chars max for best engagement`,

  tiktok: `TikTok rules:
- Short, punchy caption (150 chars ideal)
- Trending hashtags
- Conversational Gen-Z friendly tone
- Hook in first line`,

  google_my_business: `Google Business Profile rules:
- 1500 chars max
- Include business name naturally
- Local keywords
- Clear CTA with link
- Professional tone`,
}

// ── Social Post Generation ──────────────────────────────────────────────────

export interface SocialPostInput {
  merchantId: string
  platform: string
  topic: string
  posDataReference?: Record<string, unknown>
  scheduledAt?: string
}

export interface SocialPostOutput {
  hook: string
  body: string
  hashtags: string[]
  callToAction: string
  modelUsed: string
}

export async function generateSocialPost(
  input: SocialPostInput
): Promise<SocialPostOutput> {
  // Load brand voice
  const voice = await loadBrandVoice(input.merchantId)
  const platformRules = PLATFORM_RULES[input.platform] ?? ''

  const systemPrompt = `You are a social media copywriter for a local business. Write engaging content that matches the brand voice. Return valid JSON only.`

  const userPrompt = `Write a ${input.platform} post for this business:

Brand voice: ${voice ? `Tone: ${voice.tone}. Personality: ${voice.personality.join(', ')}. Target audience: ${voice.targetAudience}.` : 'Professional and engaging.'}
${voice ? `Do: ${voice.doList.join('; ')}` : ''}
${voice ? `Don't: ${voice.dontList.join('; ')}` : ''}

Topic: ${input.topic}
${input.posDataReference ? `POS context: ${JSON.stringify(input.posDataReference)}` : ''}

${platformRules}

Return JSON:
{
  "hook": "attention-grabbing opening line",
  "body": "main post body",
  "hashtags": ["relevant", "hashtags"],
  "callToAction": "clear CTA"
}`

  const response = await anthropic.messages.create({
    model: 'claude-haiku-4-20250514',
    max_tokens: 1024,
    messages: [{ role: 'user', content: userPrompt }],
    system: systemPrompt,
  })

  const textBlock = response.content.find((b) => b.type === 'text')
  if (!textBlock || textBlock.type !== 'text') {
    throw new Error('Claude Haiku returned no text')
  }

  const parsed = parseJsonResponse(textBlock.text)

  return {
    hook: String(parsed.hook ?? ''),
    body: String(parsed.body ?? ''),
    hashtags: (parsed.hashtags as string[]) ?? [],
    callToAction: String(parsed.callToAction ?? parsed.call_to_action ?? ''),
    modelUsed: 'claude-haiku-4-20250514',
  }
}

// ── SEO Article Generation ──────────────────────────────────────────────────

export interface SEOArticleInput {
  merchantId: string
  title: string
  targetKeyword: string
  secondaryKeywords?: string[]
  wordCount: number
  contentTier: 'starter' | 'growth' | 'command'
  posDataReference?: Record<string, unknown>
}

export interface SEOArticleOutput {
  title: string
  slug: string
  metaDescription: string
  body: string
  wordCount: number
  modelUsed: string
}

export async function generateSEOArticle(
  input: SEOArticleInput
): Promise<SEOArticleOutput> {
  const voice = await loadBrandVoice(input.merchantId)

  const prompt = `Write an SEO-optimized article for a local business blog.

Title: ${input.title}
Target keyword: ${input.targetKeyword}
Secondary keywords: ${(input.secondaryKeywords ?? []).join(', ')}
Word count target: ${input.wordCount}

Brand voice: ${voice ? `Tone: ${voice.tone}. Industry: ${voice.industryContext}. Local context: ${voice.localContext}.` : 'Professional, informative.'}
${input.posDataReference ? `Business data context: ${JSON.stringify(input.posDataReference)}` : ''}

Requirements:
- Use target keyword in H1, first paragraph, and naturally throughout
- Include secondary keywords where natural
- Write in a helpful, authoritative tone
- Include a meta description (150-160 chars)
- Generate a URL slug
- Use H2/H3 subheadings
- Include a CTA at the end

Return JSON:
{
  "title": "optimized article title",
  "slug": "url-friendly-slug",
  "metaDescription": "150-160 char meta description",
  "body": "full article in markdown format",
  "wordCount": actual_word_count
}`

  let responseText: string
  let modelUsed: string

  // Route: starter/growth -> DeepSeek V3, command -> Claude Sonnet
  if (input.contentTier === 'command') {
    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      messages: [{ role: 'user', content: prompt }],
      system: 'You are an expert SEO content writer. Return valid JSON only.',
    })

    const textBlock = response.content.find((b) => b.type === 'text')
    if (!textBlock || textBlock.type !== 'text') {
      throw new Error('Claude Sonnet returned no text')
    }
    responseText = textBlock.text
    modelUsed = 'claude-sonnet-4-20250514'
  } else {
    const response = await deepseekClient.chat.completions.create({
      model: DEEPSEEK_MODEL,
      messages: [
        {
          role: 'system',
          content: 'You are an expert SEO content writer. Return valid JSON only.',
        },
        { role: 'user', content: prompt },
      ],
      max_tokens: 4096,
      temperature: 0.7,
    })

    responseText = response.choices[0]?.message?.content ?? ''
    modelUsed = `deepseek:${DEEPSEEK_MODEL}`
  }

  const parsed = parseJsonResponse(responseText)

  return {
    title: String(parsed.title ?? input.title),
    slug: String(parsed.slug ?? slugify(input.title)),
    metaDescription: String(parsed.metaDescription ?? parsed.meta_description ?? ''),
    body: String(parsed.body ?? ''),
    wordCount: Number(parsed.wordCount ?? parsed.word_count ?? countWords(String(parsed.body ?? ''))),
    modelUsed,
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

async function loadBrandVoice(
  merchantId: string
): Promise<BrandVoiceProfile | null> {
  if (!supabase) return null

  const { data } = await supabase
    .from('content_brands')
    .select('voice_profile')
    .eq('merchant_id', merchantId)
    .single()

  return (data?.voice_profile as BrandVoiceProfile) ?? null
}

function parseJsonResponse(text: string): Record<string, unknown> {
  let jsonStr = text
  const match = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (match) {
    jsonStr = match[1]
  }

  try {
    return JSON.parse(jsonStr.trim()) as Record<string, unknown>
  } catch {
    throw new Error(`Failed to parse LLM JSON response: ${text.slice(0, 200)}`)
  }
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

function countWords(text: string): number {
  return text
    .replace(/[#*_`\[\]]/g, '')
    .split(/\s+/)
    .filter(Boolean).length
}
