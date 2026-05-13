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

  const { name, email, password, phone } = req.body || {}
  if (!name || !email || !password) {
    return res.status(400).json({ detail: 'Name, email, and password are required' })
  }

  try {
    const authResp = await fetch(`${supabaseUrl}/auth/v1/admin/users`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${serviceKey}`,
        'apikey': serviceKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        email_confirm: true,
        user_metadata: { full_name: name, role: 'sales_rep', portal: 'canada' },
      }),
    })

    if (!authResp.ok) {
      const authBody = await authResp.json().catch(() => ({}))
      if (authResp.status === 422 && JSON.stringify(authBody).toLowerCase().includes('already been registered')) {
        // Auth user exists — continue to upsert sales_reps
      } else {
        return res.status(400).json({ detail: authBody.msg || authBody.message || 'Could not create account' })
      }
    }

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
      console.error('sales_reps insert failed:', repResp.status, repErr)
      return res.status(400).json({ detail: 'Account created but rep profile failed. Contact admin.' })
    }

    const repData = await repResp.json()
    const repRow = Array.isArray(repData) ? repData[0] : repData

    return res.status(200).json({
      ok: true,
      rep_id: repRow?.id,
      name,
      email,
    })
  } catch (err: any) {
    console.error('Rep signup error:', err)
    return res.status(500).json({ detail: 'Internal error — please try again' })
  }
}
