// Training Course content: module definitions, quiz banks, and the Meridian
// Code of Conduct. Every question is answerable from the module's video —
// the quiz enforces watching, it isn't a trick exam.

export const PASS_SCORE = 3 // out of 4 — below this the rep rewatches

export type CourseFormat = 'landscape' | 'vertical'

export interface QuizQuestion {
  q: string
  options: string[]
  answer: number // index into options
}

export interface CourseModule {
  id: string
  title: string
  blurb: string
  files: Record<CourseFormat, string>
  quiz: QuizQuestion[]
}

export const COURSE_MODULES: CourseModule[] = [
  {
    id: 'master',
    title: 'The Full Tour',
    blurb: 'All four connections in two minutes. Watch this before anything else.',
    files: {
      landscape: 'meridian-connect-trailer.mp4',
      vertical: 'meridian-connect-trailer-vertical.mp4',
    },
    quiz: [
      {
        q: 'Which four connections make up the Meridian pitch?',
        options: [
          'Phone line, POS, cameras, costs',
          'Website, email, POS, payroll',
          'Phone line, accounting, staff scheduling, cameras',
          'POS, delivery apps, loyalty, marketing',
        ],
        answer: 0,
      },
      {
        q: 'What does the merchant do in the one-click POS connect?',
        options: [
          'Copies API keys from their dashboard',
          'Taps their provider (Square, Clover, or Stripe) and approves in the tab that opens',
          'Emails Meridian support their credentials',
          'Downloads a desktop sync app',
        ],
        answer: 1,
      },
      {
        q: 'What leaves the merchant\'s building from their cameras?',
        options: [
          'A live video feed to Meridian',
          'Daily video highlights',
          'Only the numbers — video never leaves the building',
          'Photos of each customer',
        ],
        answer: 2,
      },
      {
        q: 'What happens to the margins page once costs are loaded?',
        options: [
          'It stops estimating and starts knowing',
          'It emails a weekly PDF',
          'It hides products with low margin',
          'Nothing — margins are always exact',
        ],
        answer: 0,
      },
    ],
  },
  {
    id: 'phone',
    title: 'Phone Line Setup',
    blurb: 'Provision a number, pick a voice, load the menu, route orders.',
    files: {
      landscape: 'connect-phone.mp4',
      vertical: 'connect-phone-vertical.mp4',
    },
    quiz: [
      {
        q: 'What is the transfer number?',
        options: [
          'Meridian\'s support line',
          'The owner\'s own phone — where the agent hands off calls it can\'t handle',
          'A backup AI agent',
          'The store\'s fax line',
        ],
        answer: 1,
      },
      {
        q: 'Why must you check the menu prices during setup?',
        options: [
          'The agent quotes these prices on calls',
          'Prices are printed on invoices',
          'The POS rejects wrong prices',
          'It\'s optional — prices don\'t matter here',
        ],
        answer: 0,
      },
      {
        q: 'Where do finished phone orders go?',
        options: [
          'Into an email inbox',
          'Straight into their POS, with a text-to-pay link sent to the caller',
          'Onto a printed ticket only',
          'Into a spreadsheet the owner downloads weekly',
        ],
        answer: 1,
      },
      {
        q: 'What happens to the merchant\'s existing phone number?',
        options: [
          'They lose it',
          'They keep it — they forward it, and the AI answers from then on',
          'It becomes the transfer number automatically',
          'Meridian ports it into the platform permanently',
        ],
        answer: 1,
      },
    ],
  },
  {
    id: 'pos',
    title: 'POS Connect',
    blurb: 'One-click connect (Square, Clover, Stripe) and the first sync.',
    files: {
      landscape: 'connect-pos.mp4',
      vertical: 'connect-pos-vertical.mp4',
    },
    quiz: [
      {
        q: 'In one-click connect, whose Square/Clover account signs in?',
        options: [
          'The rep\'s demo account',
          'Meridian\'s master account',
          'The merchant\'s own account — have THEM do this part',
          'Any account works',
        ],
        answer: 2,
      },
      {
        q: 'What does First Sync import?',
        options: [
          'Only today\'s sales',
          'Up to eighteen months of history — products, sales, refunds',
          'Customer phone numbers',
          'Staff schedules',
        ],
        answer: 1,
      },
      {
        q: 'What must exist BEFORE the merchant can connect their POS?',
        options: [
          'A signed annual contract',
          'The account must be provisioned from your sales portal first',
          'A camera connection',
          'A cost sheet upload',
        ],
        answer: 1,
      },
      {
        q: 'The provider sign-in tab never appears. First thing to check?',
        options: [
          'The popup blocker',
          'The merchant\'s wifi router',
          'Meridian server status',
          'Their Square subscription tier',
        ],
        answer: 0,
      },
    ],
  },
  {
    id: 'camera',
    title: 'Camera Setup',
    blurb: 'Three ways to connect a camera, zones, and the privacy story.',
    files: {
      landscape: 'connect-camera.mp4',
      vertical: 'connect-camera-vertical.mp4',
    },
    quiz: [
      {
        q: 'Merchants get nervous about cameras. What do you lead with?',
        options: [
          'The video never leaves their store — Meridian only reports numbers',
          'The footage is stored encrypted in the cloud',
          'Only managers can watch the feed',
          'Recording is optional',
        ],
        answer: 0,
      },
      {
        q: 'How long is the pairing code valid?',
        options: ['Five minutes', 'Fifteen minutes — run it while you\'re together', 'One hour', 'It never expires'],
        answer: 1,
      },
      {
        q: 'What privacy setting do you leave on, and what does it promise?',
        options: [
          'Anonymous — counting, not identifying. It\'s the default.',
          'Face-match — for loyalty rewards',
          'Cloud backup — for insurance claims',
          'Audio capture — for staff coaching',
        ],
        answer: 0,
      },
      {
        q: 'Which set of metrics do cameras feed into analytics?',
        options: [
          'Walk-ins, occupancy, queue times, and walk-in-to-sale conversion',
          'Employee attendance and breaks',
          'Customer age and gender profiles',
          'Vehicle counts and license plates',
        ],
        answer: 0,
      },
    ],
  },
  {
    id: 'csv',
    title: 'Costs & Real Margins',
    blurb: 'Upload a cost sheet and switch margins from estimates to real numbers.',
    files: {
      landscape: 'connect-csv.mp4',
      vertical: 'connect-csv-vertical.mp4',
    },
    quiz: [
      {
        q: 'Before costs are loaded, what are the margin numbers?',
        options: [
          'Hidden entirely',
          'Estimates — and they\'re labeled that way',
          'Exact, pulled from the POS',
          'Set manually by the merchant',
        ],
        answer: 1,
      },
      {
        q: 'What does the second upload button accept?',
        options: [
          'Only Excel files',
          'Almost anything — a PDF supplier invoice, a spreadsheet, even a photo of a delivery sheet',
          'Only photos',
          'Signed purchase orders only',
        ],
        answer: 1,
      },
      {
        q: 'What happens to lines Meridian couldn\'t match?',
        options: [
          'They\'re silently dropped',
          'They\'re listed so nothing silently slips through — fix the names or ignore them',
          'The whole upload fails',
          'They get a default cost of zero',
        ],
        answer: 1,
      },
      {
        q: 'What should you tell the merchant to bring to onboarding?',
        options: [
          'Their tax returns',
          'One recent supplier invoice',
          'Last year\'s P&L',
          'Their landlord\'s contact info',
        ],
        answer: 1,
      },
    ],
  },
]

// ─── Code of Conduct ─────────────────────────────────────────

export const CONDUCT_VERSION = '1.0'

export interface ConductSection {
  title: string
  rules: string[]
}

export const CODE_OF_CONDUCT: ConductSection[] = [
  {
    title: 'Who you are (and aren\'t)',
    rules: [
      'You represent Meridian as a sales rep. You are not authorized to sign agreements on Meridian\'s behalf, or to invent custom pricing, discounts, refunds, or contract terms beyond the published plans without written approval.',
      'Never present yourself as an engineer, lawyer, accountant, or Meridian executive.',
    ],
  },
  {
    title: 'Claims you may never make',
    rules: [
      'Never guarantee revenue, sales lift, cost savings, or any specific ROI number. You may share real product capabilities; outcomes vary by business.',
      'Never claim Meridian is a bank, a payment processor, or a point-of-sale system. Meridian connects to the merchant\'s POS (Square/Clover); payments are processed by those providers.',
      'Never promise unreleased features, dates, or roadmap items as if they exist today. If it isn\'t in your training materials, don\'t sell it.',
      'Never say the camera product records, monitors, or identifies people. Camera analytics are anonymous counts — walk-ins, queues, conversion. No facial recognition, ever.',
      'Never tell a caller or merchant that the AI phone agent is a human, and never deny it\'s AI when asked.',
      'Never quote prices other than the published plan pricing in the portal.',
    ],
  },
  {
    title: 'Privacy & compliance',
    rules: [
      'Never advise a merchant to skip consent, signage, or disclosure obligations (PIPEDA, Quebec Law 25, or any local rule). If they have compliance questions you can\'t answer from the guides, escalate — don\'t improvise.',
      'Never ask for, handle, or store a merchant\'s passwords. The merchant signs into their own Square/Clover account during connect — always.',
      'Never give legal, tax (GST/HST), or accounting advice.',
    ],
  },
  {
    title: 'Honest selling',
    rules: [
      'No fabricated testimonials, metrics, or customer names. No fake urgency ("price doubles tomorrow").',
      'Present estimates as estimates. If a dashboard number is labeled estimated, say so.',
      'Don\'t make false statements about competitors. Beat them on the product.',
    ],
  },
  {
    title: 'Data handling',
    rules: [
      'Lead and merchant data stays in the portal. Never export, share, or sell it outside Meridian systems.',
      'Use only approved Meridian materials — decks, proposals, and videos from the portal.',
    ],
  },
]

export const CONDUCT_ACKNOWLEDGEMENT =
  'I have read and understood the Meridian Sales Rep Code of Conduct. I agree to follow it, and I understand that violations may result in suspension of my portal access, loss of unpaid commissions where permitted by my rep agreement, and termination of that agreement.'
