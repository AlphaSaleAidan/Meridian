// Public terms of service — required (with the privacy policy) by integration
// vendors' developer-portal applications. Factual and conservative; route
// changes through counsel review.
const SECTIONS: { heading: string; body: string[] }[] = [
  {
    heading: 'The service',
    body: [
      'Meridian Intelligence provides analytics, forecasting and operational tools for restaurants and retailers, computed from data sources you choose to connect (point-of-sale systems, payment processors and other integrations).',
    ],
  },
  {
    heading: 'Your account',
    body: [
      'You are responsible for the accuracy of the information you provide and for keeping your credentials secure. You must have the authority to connect any data source you connect.',
    ],
  },
  {
    heading: 'Connected services',
    body: [
      'Integrations are authorized by you through each provider’s own consent flow and can be disconnected at any time from Settings. Your use of each connected service remains governed by that provider’s terms.',
    ],
  },
  {
    heading: 'Acceptable use',
    body: [
      'Do not attempt to access other merchants’ data, probe or disrupt the service, or use it to violate any law or third-party agreement.',
    ],
  },
  {
    heading: 'Billing',
    body: [
      'Paid plans are billed as described at purchase. You may cancel at any time; service continues through the end of the paid period.',
    ],
  },
  {
    heading: 'Disclaimers',
    body: [
      'Analytics, forecasts and insights are decision support, not guarantees. The service is provided “as is” to the maximum extent permitted by law; our aggregate liability is limited to the fees you paid in the twelve months preceding a claim.',
    ],
  },
  {
    heading: 'Changes and contact',
    body: [
      'We may update these terms; material changes will be announced in-product or by email. Questions: support@meridian.tips.',
    ],
  },
]

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0B0B0E] text-[#F5F5F7]">
      <div className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold">Terms of Service</h1>
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
