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

// ── Core marketing principles applied to every post ────────────────────────

const MARKETING_PRINCIPLES = `MARKETING PRINCIPLES (apply to every post):

HOOK FORMULA — first line must stop the scroll. Use one of:
  • Data hook: Lead with a specific number from POS data ("23% of our revenue comes from one dish")
  • Curiosity gap: Tease without revealing ("The drink our baristas won't stop making")
  • Bold claim: Confident statement ("Best oil change in town — our data proves it")
  • Social proof: Implied demand ("This sold out 3 weekends in a row")

BODY STRUCTURE:
  • Open with the hook, then deliver the payoff within 2 sentences
  • Weave in ONE specific POS data point naturally (revenue %, order count, popularity rank)
  • Keep it conversational — write like a passionate owner, not a marketing agency
  • Use short paragraphs (1-2 sentences each) with line breaks between
  • End with urgency or scarcity when genuine ("limited batch", "weekend only", "first 50")

CALL TO ACTION:
  • One CTA per post, specific and actionable
  • Use "Visit", "Book", "Order", "Try" — never "Click here" or "Check it out"
  • Include location or link-in-bio reference when relevant

TONE RULES:
  • Sound like a real person who loves their business, not a corporation
  • Never use "we are excited to announce", "proud to share", or "don't miss out"
  • No "Introducing our...", "We're thrilled...", or any filler corporate-speak
  • Contractions always (we're, it's, you'll), never formal (we are, it is, you will)
  • Reference the specific product/item by its menu name, not generic descriptions

HASHTAG STRATEGY:
  • Mix: 2-3 branded (#ShopName), 2-3 niche (#LocalEats, #CraftCoffee), 2-3 discovery (#FoodTok)
  • Never use generic spam tags (#love, #instagood, #follow)
  • Put hashtags AFTER the body, separated by a blank line`

const PLATFORM_RULES: Record<string, string> = {
  instagram: `Instagram rules:
- Max 300 chars for feed (people don't expand)
- Hook must work as a standalone caption visible in the grid
- 8-12 relevant hashtags after a line break
- Pair with a mouthwatering/eye-catching image description
- Use line breaks every 1-2 sentences for mobile readability
- End before the "...more" cutoff (~125 chars) with something compelling`,

  facebook: `Facebook rules:
- 1-3 short paragraphs, conversational neighborhood-friend tone
- Ask a genuine question that people will answer in comments
- 1-3 hashtags max (Facebook penalizes hashtag-heavy posts)
- Encourage shares by making it relatable ("Tag someone who needs this")
- Link in CTA if applicable`,

  twitter: `Twitter/X rules:
- Max 280 chars total — every word must earn its place
- One punchy idea, no filler
- 1-2 hashtags woven into the sentence naturally
- End with engagement prompt or link`,

  linkedin: `LinkedIn rules:
- Professional but human — think "smart business owner sharing insights"
- Open with a hook line, then line break for suspense
- Use data points to establish authority
- 3-5 industry-relevant hashtags
- 1000 chars max for best engagement`,

  tiktok: `TikTok rules:
- 80-150 chars max — caption is secondary to the visual
- Conversational, slightly cheeky tone
- Use trending sounds/hashtag references when relevant
- Hook = first 5 words that make someone stop scrolling`,

  google_my_business: `Google Business Profile rules:
- 750 chars ideal (Google truncates after ~1500)
- Naturally include business name, city, and service keywords for local SEO
- Always include a clear CTA with specific action (call, visit, book online)
- Professional but warm — you're appearing in search results, not social feeds
- Mention specific products/services by name for long-tail keyword matches`,
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

  const systemPrompt = `You are a top-tier social media copywriter who specializes in local business marketing. You write scroll-stopping posts that feel authentic, data-driven, and make people want to visit. You never sound corporate or generic. Return valid JSON only.`

  const userPrompt = `Write a ${input.platform} post for this local business.

${MARKETING_PRINCIPLES}

${platformRules}

BRAND VOICE:
${voice ? `Tone: ${voice.tone}
Personality: ${voice.personality.join(', ')}
Target audience: ${voice.targetAudience}
Always do: ${voice.doList.join('; ')}
Never do: ${voice.dontList.join('; ')}
On-brand phrases: ${voice.samplePhrases?.join('; ') ?? 'none provided'}` : 'Tone: Confident, approachable small business owner. Never corporate.'}

TOPIC: ${input.topic}

${input.posDataReference ? `POS DATA (use at least one data point naturally in the copy):
${JSON.stringify(input.posDataReference, null, 2)}` : 'No POS data available — write based on the topic alone.'}

Write the post now. The hook should stop someone mid-scroll. The body should make them want to visit or buy. The CTA should tell them exactly what to do next.

Return JSON:
{
  "hook": "scroll-stopping opening line (this appears before the fold — make it count)",
  "body": "main post body with line breaks between paragraphs",
  "hashtags": ["branded", "niche", "discovery"],
  "callToAction": "specific, actionable CTA"
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

  const prompt = `Write an SEO article that ranks on Google AND gets cited by AI assistants (ChatGPT, Perplexity, Claude).

ARTICLE BRIEF:
- Title: ${input.title}
- Target keyword: "${input.targetKeyword}"
- Secondary keywords: ${(input.secondaryKeywords ?? []).join(', ') || 'none specified'}
- Word count: ${input.wordCount} words

BRAND CONTEXT:
${voice ? `Tone: ${voice.tone}. Industry: ${voice.industryContext}. Local context: ${voice.localContext}.
On-brand phrases: ${voice.samplePhrases?.join('; ') ?? 'none'}` : 'Professional, informative, locally-authoritative.'}
${input.posDataReference ? `\nREAL BUSINESS DATA (weave into the article as proof points):\n${JSON.stringify(input.posDataReference, null, 2)}` : ''}

SEO PRINCIPLES:
- Target keyword in H1, first 100 words, one H2, meta description, and naturally 3-5 more times
- Secondary keywords in at least one H2/H3 each
- Write in a helpful, authoritative tone — the article should be the BEST answer to the search query
- Structure: intro → 3-5 H2 sections → conclusion with CTA
- Use H2/H3 subheadings phrased as questions people actually search ("How much does X cost?")
- Include specific numbers, prices, and data points — AI models cite articles with concrete facts
- Mention the business name and city naturally (not stuffed) for local SEO
- End with a clear CTA that drives visits or bookings

AI CITATION OPTIMIZATION:
- Write definitive statements AI can quote: "The best X in [city] is Y because..."
- Include structured comparisons, lists, and FAQ-style Q&A sections
- Answer the "People Also Ask" questions for the target keyword
- Be specific enough that an AI assistant would reference this over a generic article

META REQUIREMENTS:
- Meta description: 150-160 chars, includes target keyword, compelling click-through
- URL slug: short, keyword-rich, no filler words

Return JSON:
{
  "title": "SEO-optimized article title with target keyword",
  "slug": "keyword-rich-url-slug",
  "metaDescription": "150-160 char meta description with keyword and CTA",
  "body": "full article in markdown (H2/H3 headings, paragraphs, lists)",
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
