/**
 * DeepSeek client via OpenAI-compatible SDK.
 * Uses DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL.
 */

import OpenAI from 'openai'

export const DEEPSEEK_MODEL = 'deepseek-chat'

export const deepseekClient = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY ?? '',
  baseURL: process.env.DEEPSEEK_BASE_URL ?? 'https://api.deepseek.com',
})
