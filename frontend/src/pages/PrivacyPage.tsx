// Public privacy policy — a hard prerequisite for every integration vendor's
// developer-portal application (Intuit, Xero, Uber, Gusto, Mailchimp all
// require a live privacy URL and several verify it loads). Content is
// deliberately factual and conservative; route legal review through counsel
// before any claim is strengthened.
const SECTIONS: { heading: string; body: string[] }[] = [
  {
    heading: 'What we collect',
    body: [
      'Account information you provide: name, business name, email address and password (stored as a salted hash by our authentication provider).',
      'Point-of-sale and connected-service data you authorize: when you connect a POS or other integration, we receive the data covered by the read-only scopes you approve on that provider’s consent screen — typically sales transactions, catalog items, inventory levels and anonymized labor summaries. We do not request write access to your POS.',
      'Usage data: standard server logs (IP address, browser type, pages viewed) used for security and reliability.',
    ],
  },
  {
    heading: 'How we use it',
    body: [
      'To provide the Meridian analytics service: dashboards, forecasts, insights and alerts computed from your connected data.',
      'To operate, secure and improve the service. We do not sell your data, and we do not use one merchant’s data to benefit another merchant.',
    ],
  },
  {
    heading: 'How it is stored and protected',
    body: [
      'Data is hosted with our infrastructure providers (Supabase, Railway, Vercel). OAuth access and refresh tokens for connected services are encrypted at rest with AES-256-GCM.',
      'Access to production systems is restricted and logged.',
    ],
  },
  {
    heading: 'Third-party services',
    body: [
      'We share data only with processors needed to run the service: hosting (Supabase, Railway, Vercel), payments (Stripe), email delivery (Resend), and telephony when you enable phone ordering (Vapi, Telnyx). Each receives only what its function requires.',
    ],
  },
  {
    heading: 'Disconnecting and deletion',
    body: [
      'You can disconnect any integration at any time from Settings; we revoke the token and stop syncing.',
      'You can request deletion of your account and associated data by emailing us; we complete verified deletion requests within 30 days.',
    ],
  },
  {
    heading: 'Contact',
    body: [
      'Privacy questions: support@meridian.tips.',
    ],
  },
]

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#0B0B0E] text-[#F5F5F7]">
      <div className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold">Privacy Policy</h1>
        <p className="text-sm text-[#A1A1A8] mt-2">
          Meridian Intelligence (operated by ASP EPC1) &mdash; last updated August 12, 2026
        </p>
        <div className="mt-10 space-y-8">
          {SECTIONS.map(s => (
            <section key={s.heading}>
              <h2 className="text-lg font-semibold text-[#F5F5F7]">{s.heading}</h2>
              <div className="mt-2 space-y-2">
                {s.body.map((p, i) => (
                  <p key={i} className="text-sm leading-relaxed text-[#A1A1A8]">{p}</p>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
