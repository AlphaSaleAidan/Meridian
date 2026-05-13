import type { VercelRequest, VercelResponse } from '@vercel/node'

const CANADA_ORG_ID = '168b6df2-e9af-4b00-8fec-51e51149ff19'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (req.method === 'OPTIONS') return res.status(200).end()
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' })

  const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || ''
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || ''

  if (!supabaseUrl || !serviceKey) {
    return res.status(503).json({ detail: 'Service temporarily unavailable' })
  }

  const body = req.body || {}
  const name = body.name?.trim()
  const email = body.email?.trim()?.toLowerCase()
  const phone = body.phone?.trim() || ''
  const position = body.position || 'sales_rep'

  if (!name || !email) {
    return res.status(400).json({ detail: 'Name and email are required' })
  }

  try {
    const appId = crypto.randomUUID()

    // Insert applicant into sales_reps (pending approval)
    const insertResp = await fetch(`${supabaseUrl}/rest/v1/sales_reps`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${serviceKey}`,
        'apikey': serviceKey,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
      },
      body: JSON.stringify({
        org_id: CANADA_ORG_ID,
        name,
        email,
        phone,
        commission_rate: 0.70,
        is_active: false,
        portal_context: 'canada',
      }),
    })

    if (insertResp.ok) {
      return res.status(200).json({
        status: 'received',
        application_id: appId,
        name,
        position,
        message: "Your application has been received. We'll be in touch soon!",
      })
    }

    // If duplicate email (already applied), treat as success
    const errText = await insertResp.text()
    if (insertResp.status === 409 || errText.includes('23505') || errText.includes('duplicate')) {
      return res.status(200).json({
        status: 'received',
        application_id: appId,
        name,
        position,
        message: "Your application has been received. We'll be in touch soon!",
      })
    }

    console.error('sales_reps insert failed:', insertResp.status, errText)
    return res.status(500).json({ detail: 'Could not save application. Please try again.' })
  } catch (err: any) {
    console.error('Career apply error:', err?.message || err)
    return res.status(500).json({ detail: 'Something went wrong. Please try again.' })
  }
}
