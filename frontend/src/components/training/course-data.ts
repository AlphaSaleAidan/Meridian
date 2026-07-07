// Training Course content: module definitions, quiz banks, and the Meridian
// Code of Conduct. Every question is answerable from the module's video —
// the quiz enforces watching, it isn't a trick exam.

export const PASS_SCORE = 6 // out of 10 — below this the rep rewatches

export type CourseFormat = 'landscape' | 'vertical' | 'brainrot'

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
      brainrot: 'meridian-connect-trailer-brainrot.mp4',
    },
    quiz: [
      {
        q: 'How many things does Meridian connect for a merchant?',
        options: ['Two', 'Three', 'Four', 'Six'],
        answer: 2,
      },
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
        q: 'What does the AI phone agent do with calls it can\'t handle?',
        options: [
          'Hangs up politely',
          'Hands them to the owner\'s real phone line',
          'Takes a voicemail and emails it',
          'Asks the caller to try again later',
        ],
        answer: 1,
      },
      {
        q: 'How many studio voices can the merchant choose from?',
        options: ['Three', 'Five', 'Eight', 'Twelve'],
        answer: 2,
      },
      {
        q: 'How much sales history does Meridian pull when the POS connects?',
        options: ['30 days', '6 months', 'Up to 18 months', 'Everything since the account opened'],
        answer: 2,
      },
      {
        q: 'What does the merchant do in the one-click POS connect?',
        options: [
          'Copies API keys from their dashboard',
          'Taps Square or Clover and approves in the tab that opens',
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
        q: 'Which camera metrics does Meridian report?',
        options: [
          'Faces and names of repeat customers',
          'Walk-ins, queues, and how many visitors actually buy',
          'Staff break times',
          'License plates in the parking lot',
        ],
        answer: 1,
      },
      {
        q: 'What can a merchant drop in to load their costs?',
        options: [
          'Only a formatted CSV template',
          'A supplier invoice or cost sheet — CSV, spreadsheet, even a photo',
          'Only receipts scanned in the mobile app',
          'A QuickBooks export exclusively',
        ],
        answer: 1,
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
      brainrot: 'connect-phone-brainrot.mp4',
    },
    quiz: [
      {
        q: 'Where does phone setup start in the customer portal?',
        options: [
          'Settings → Integrations',
          'Phone Calls → Set up',
          'Dashboard → Add-ons',
          'You call Meridian support to start it',
        ],
        answer: 1,
      },
      {
        q: 'How does the business get its phone number in step one?',
        options: [
          'The merchant ports their number in, which takes a week',
          'Meridian provisions a dedicated number automatically',
          'The rep buys one from Telnyx manually',
          'They reuse the owner\'s cell number',
        ],
        answer: 1,
      },
      {
        q: 'The merchant doesn\'t like the number they got. What do you do?',
        options: [
          'Open a support ticket',
          'Press the Swap button — a new number instantly',
          'Tell them numbers can\'t be changed',
          'Reinstall the phone agent',
        ],
        answer: 1,
      },
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
        q: 'What do you configure in step two?',
        options: [
          'Payment processing',
          'Business name and the greeting callers will hear',
          'Staff accounts',
          'Delivery zones',
        ],
        answer: 1,
      },
      {
        q: 'How should you demo the voices to a merchant?',
        options: [
          'Describe them from memory',
          'Press play on the real samples so they hear what callers will hear',
          'Call the line eight times',
          'Send them a YouTube link',
        ],
        answer: 1,
      },
      {
        q: 'Which is NOT one of the three ways to load the menu?',
        options: [
          'Scan a printed menu with the camera',
          'Import a CSV',
          'Sync from their POS after it\'s connected',
          'Dictate it to the AI over a phone call',
        ],
        answer: 3,
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
    blurb: 'One-click Square/Clover connect and the first sync.',
    files: {
      landscape: 'connect-pos.mp4',
      vertical: 'connect-pos-vertical.mp4',
      brainrot: 'connect-pos-brainrot.mp4',
    },
    quiz: [
      {
        q: 'Where does the merchant start the POS connection?',
        options: [
          'A banner on their home screen: Connect your POS',
          'An email link from Meridian',
          'The rep connects it from the sales portal',
          'Square\'s app marketplace',
        ],
        answer: 0,
      },
      {
        q: 'What are the four steps of the POS wizard?',
        options: [
          'Login, Pay, Sync, Done',
          'Welcome, Connect, First Sync, Confirm',
          'Choose, Verify, Import, Review',
          'Connect, Map, Test, Launch',
        ],
        answer: 1,
      },
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
        q: 'After the merchant presses Allow in the provider tab, what happens?',
        options: [
          'They copy a code back into Meridian',
          'The original tab notices automatically — no copying anything',
          'They wait for a confirmation email',
          'The rep enters an API key',
        ],
        answer: 1,
      },
      {
        q: 'Who is the API-key path for?',
        options: [
          'Square merchants only',
          'Clover merchants who prefer it — paste the API key and merchant ID',
          'Merchants without internet',
          'Enterprise accounts only',
        ],
        answer: 1,
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
        q: 'A large merchant\'s first sync is taking a few minutes. What\'s true?',
        options: [
          'Something is broken — reconnect immediately',
          'That\'s normal; the page updates itself every few seconds',
          'You must refresh the browser manually',
          'The sync must be restarted after 60 seconds',
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
      {
        q: 'A sync fails after setup. What does the video say to do?',
        options: [
          'The portal shows it — just reconnect',
          'Delete the account and start over',
          'Email engineering',
          'Wait 24 hours for auto-repair',
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
      brainrot: 'connect-camera-brainrot.mp4',
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
        q: 'What is the first question when you press Add Camera?',
        options: [
          'What brand is your camera?',
          'How is your camera connected?',
          'How many cameras do you have?',
          'Where is your router?',
        ],
        answer: 1,
      },
      {
        q: 'Which option is the easiest, per the video?',
        options: [
          'Manual RTSP',
          'Smart-app camera — sign into the Smart Life or Tuya account and pick the cameras',
          'Local network connector',
          'Shipping the camera to Meridian',
        ],
        answer: 1,
      },
      {
        q: 'How does the local network connector work?',
        options: [
          'You install an app on the camera itself',
          'A one-line command run on any computer in the store on the same wifi — it finds the cameras by itself',
          'You plug a Meridian box into the router',
          'You forward ports on the modem',
        ],
        answer: 1,
      },
      {
        q: 'How long is the pairing code valid?',
        options: ['Five minutes', 'Fifteen minutes — run it while you\'re together', 'One hour', 'It never expires'],
        answer: 1,
      },
      {
        q: 'What does the manual option ask for?',
        options: [
          'The camera\'s RTSP address from its admin panel',
          'The camera\'s serial number',
          'A photo of the camera',
          'The merchant\'s wifi password',
        ],
        answer: 0,
      },
      {
        q: 'What are detection zones for?',
        options: [
          'Blurring parts of the image',
          'Telling Meridian what each area means — Door, Register, Seating',
          'Setting recording schedules',
          'Adjusting brightness per region',
        ],
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
        q: 'How soon do the first numbers arrive after activation?',
        options: ['Instantly', 'Within about fifteen minutes', 'The next morning', 'After one full week'],
        answer: 1,
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
      brainrot: 'connect-csv-brainrot.mp4',
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
        q: 'Which page do you open to load costs?',
        options: ['Dashboard', 'The Margins page', 'Settings → Billing', 'Inventory → Suppliers'],
        answer: 1,
      },
      {
        q: 'What can the cost CSV contain?',
        options: [
          'Item name and unit cost, or a stock-up receipt with totals and quantities',
          'Only barcodes and prices',
          'Only Meridian\'s exact template',
          'Sales totals by day',
        ],
        answer: 0,
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
        q: 'How does Meridian match uploaded lines to products?',
        options: [
          'By barcode only',
          'To the product catalog by name',
          'By price similarity',
          'It doesn\'t — you map every line by hand',
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
        q: 'When do margins recalculate with real numbers?',
        options: [
          'Overnight',
          'The moment it saves',
          'After an admin approves',
          'On the first of the month',
        ],
        answer: 1,
      },
      {
        q: 'At what levels do margins recalculate?',
        options: [
          'Store total only',
          'Per product, per category, and across the whole menu',
          'Per supplier only',
          'Per transaction only',
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
      {
        q: 'Why does the video call real margins the fastest "wow"?',
        options: [
          'The merchant leaves with real margins on day one',
          'It unlocks a discount',
          'It makes the dashboard load faster',
          'It\'s required before the POS will sync',
        ],
        answer: 0,
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
