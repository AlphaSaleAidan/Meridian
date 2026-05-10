import { posSystems, type POSSystem, type MerchantRequirement } from '@/data/pos-systems'

export function getPosSystem(key: string): POSSystem | undefined {
  return posSystems.find(s => s.key === key)
}

export function getMerchantRequirements(system: POSSystem): MerchantRequirement[] {
  if (system.merchantRequirements?.length) return system.merchantRequirements

  const auth = system.authMethod ?? (
    system.integrationStatus.oauthSupported ? 'oauth2' :
    system.integrationStatus.apiAvailable ? 'api_key' :
    'manual_export'
  )
  const creds = system.connectionRequirements.requiredCredentials
  const prefix = system.key.replace(/-/g, '_')

  if (auth === 'oauth2') {
    const fields: MerchantRequirement[] = [
      {
        label: `Connect with ${system.name}`,
        fieldId: `${prefix}_oauth`,
        fieldType: 'oauth_button',
        placeholder: `Connect with ${system.name}`,
        howToFind: `Click the button to authorize Meridian with your ${system.name} account.`,
        required: true,
      },
    ]
    for (const cred of creds) {
      if (/login|account|oauth/i.test(cred)) continue
      fields.push({
        label: cred,
        fieldId: `${prefix}_${cred.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`,
        fieldType: 'text',
        placeholder: `Enter ${cred}`,
        howToFind: `Check your ${system.name} dashboard or account settings.`,
        required: false,
      })
    }
    return fields
  }

  if (auth === 'manual_export') {
    return [{
      label: `Upload ${system.contingencyPlan.dataExportFormat || 'CSV'} Export`,
      fieldId: `${prefix}_upload`,
      fieldType: 'file_upload',
      placeholder: `Upload ${system.contingencyPlan.dataExportFormat || 'CSV'} from ${system.name}`,
      howToFind: system.contingencyPlan.exportInstructions || `Export data from your ${system.name} back-office.`,
      required: true,
    }]
  }

  if (auth === 'coming_soon') return []

  const fields: MerchantRequirement[] = []

  if (auth === 'api_key_plus_secret') {
    fields.push(
      { label: 'API Key', fieldId: `${prefix}_api_key`, fieldType: 'password', placeholder: 'Enter API Key', howToFind: `Find in ${system.name} → Settings → API / Integrations.`, required: true },
      { label: 'API Secret', fieldId: `${prefix}_api_secret`, fieldType: 'password', placeholder: 'Enter API Secret', howToFind: `Find alongside your API Key in ${system.name} settings.`, required: true },
    )
  } else if (auth === 'username_password') {
    fields.push(
      { label: 'Username', fieldId: `${prefix}_username`, fieldType: 'text', placeholder: 'Enter username', howToFind: `Your ${system.name} login username.`, required: true },
      { label: 'Password', fieldId: `${prefix}_password`, fieldType: 'password', placeholder: 'Enter password', howToFind: `Your ${system.name} login password.`, required: true },
    )
  } else {
    let hasApiKey = false
    for (const cred of creds) {
      const lower = cred.toLowerCase()
      if (/login|account/i.test(lower)) continue
      const id = `${prefix}_${lower.replace(/[^a-z0-9]+/g, '_')}`
      const isSecret = /secret|password|key|token/i.test(lower)
      fields.push({
        label: cred,
        fieldId: id,
        fieldType: isSecret ? 'password' : 'text',
        placeholder: `Enter ${cred}`,
        howToFind: `Find in ${system.name} → Settings → API / Integrations.`,
        required: true,
      })
      if (/key/i.test(lower)) hasApiKey = true
    }
    if (fields.length === 0 || !hasApiKey) {
      fields.unshift({
        label: `${system.name} API Key`,
        fieldId: `${prefix}_api_key`,
        fieldType: 'password',
        placeholder: 'Enter API Key',
        howToFind: `Find in ${system.name} → Settings → API / Integrations.`,
        required: true,
      })
    }
  }

  return fields
}

export function validateCredentials(
  system: POSSystem,
  values: Record<string, string>,
): { valid: boolean; errors: Record<string, string> } {
  const reqs = getMerchantRequirements(system)
  const errors: Record<string, string> = {}

  for (const req of reqs) {
    if (req.required && req.fieldType !== 'oauth_button' && !values[req.fieldId]?.trim()) {
      errors[req.fieldId] = `${req.label} is required`
    }
  }

  return { valid: Object.keys(errors).length === 0, errors }
}

export function serializeCredentials(
  system: POSSystem,
  values: Record<string, string>,
): { provider: string; credentials: Record<string, string> } {
  const reqs = getMerchantRequirements(system)
  const credentials: Record<string, string> = {}

  for (const req of reqs) {
    if (req.fieldType === 'oauth_button') continue
    const val = values[req.fieldId]?.trim()
    if (val) credentials[req.fieldId] = val
  }

  return { provider: system.key, credentials }
}
