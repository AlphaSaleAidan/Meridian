import type { VercelRequest, VercelResponse } from '@vercel/node'

const CANADA_ORG_ID = '168b6df2-e9af-4b00-8fec-51e51149ff19'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    return res.status(200).end()
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method not allowed' })
  }

  const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || ''
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || ''

  if (!supabaseUrl || !serviceKey) {
    return res.status(503).json({ detail: 'Supabase not configured' })
  }

  const { name, email, phone, position, city, province, experience, employer, linkedin, heardFrom, availability, message } = req.body || {}

  if (!name || !email || !position) {
    return res.status(400).json({ detail: 'Name, email, and position are required' })
  }

  try {
    // 1. Try to insert into career_applications (may not exist yet)
    const appId = crypto.randomUUID()
    const now = new Date().toISOString()

    const appResp = await fetch(`${supabaseUrl}/rest/v1/career_applications`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${serviceKey}`,
        'apikey': serviceKey,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
      },
      body: JSON.stringify({
        id: appId,
        country: 'CA',
        name,
        email,
        phone: phone || '',
        position,
        city: city || '',
        state_province: province || '',
        experience: experience || '',
        current_employer: employer || '',
        linkedin_url: linkedin || '',
        referral_source: heardFrom || '',
        availability: availability || '',
        motivation: message || '',
        status: 'pending',
        created_at: now,
      }),
    })

    if (!appResp.ok) {
      console.log('career_applications insert skipped (table may not exist):', appResp.status)
    }

    // 2. Upsert into sales_reps so the applicant shows up in Team Management
    const repResp = await fetch(`${supabaseUrl}/rest/v1/sales_reps`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${serviceKey}`,
        'apikey': serviceKey,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation,resolution=merge-duplicates',
      },
      body: JSON.stringify({
        org_id: CANADA_ORG_ID,
        name,
        email,
        phone: phone || '',
        commission_rate: 0.70,
        is_active: false,
        portal_context: 'canada',
      }),
    })

    if (!repResp.ok) {
      const repErr = await repResp.text()
      console.error('sales_reps upsert failed:', repResp.status, repErr)
      return res.status(500).json({ detail: 'Could not save application. Please try again.' })
    }

    return res.status(200).json({
      status: 'received',
      application_id: appId,
      name,
      position,
      message: "Your application has been received. We'll be in touch soon!",
    })
  } catch (err: any) {
    console.error('Career application error:', err)
    return res.status(500).json({ detail: 'Internal error — please try again' })
  }
}
