import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import SEO from '@/components/SEO'
import MeridianLogo from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'

const EASE = [0.16, 1, 0.3, 1] as const

const LEGAL_ENTITY = 'Meridian'
const CONTACT_EMAIL = 'legal@meridian.tips'
const SUPPORT_EMAIL = 'support@meridian.tips'
const GOVERNING_STATE = 'Delaware'
const EFFECTIVE_DATE = 'June 4, 2026'

export default function TermsPage() {
  const navigate = useNavigate()

  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100">
      <SEO
        title="Terms of Service — Meridian"
        description="The terms governing your use of Meridian's AI phone agent, SMS ordering, and POS analytics services."
        path="/terms"
      />
      <GrainOverlay />

      <header className="sticky top-0 z-20 border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-sm text-zinc-400 transition hover:text-zinc-100"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </button>
          <MeridianLogo className="h-7" />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          <p className="text-sm uppercase tracking-widest text-zinc-500">Legal</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight md:text-5xl">Terms of Service</h1>
          <p className="mt-4 text-sm text-zinc-500">Effective {EFFECTIVE_DATE}</p>
        </motion.div>

        <article className="prose prose-invert prose-zinc mt-12 max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-h2:mt-12 prose-h2:text-2xl prose-h3:mt-8 prose-h3:text-lg prose-p:text-zinc-300 prose-li:text-zinc-300 prose-strong:text-zinc-100 prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline">
          <p>
            Welcome to {LEGAL_ENTITY} (&ldquo;<strong>Meridian</strong>,&rdquo; &ldquo;we,&rdquo;
            &ldquo;our&rdquo;). These Terms of Service (&ldquo;Terms&rdquo;) govern your use of our
            AI phone ordering service, SMS-based ordering, payment-link delivery, POS analytics
            dashboard, and any related services we provide (collectively, the
            &ldquo;Services&rdquo;).
          </p>
          <p>
            By using the Services — including by calling or texting a phone number powered by
            Meridian — you agree to these Terms. If you do not agree, do not use the Services.
          </p>

          <h2>1. What we provide</h2>
          <p>
            Meridian offers an AI-powered phone agent that takes voice orders for participating
            restaurants and similar merchants, an SMS-based ordering interface, automated payment-
            link delivery, and analytics tools for merchants. The Services are provided to two
            categories of users:
          </p>
          <ul>
            <li>
              <strong>Merchants</strong> — businesses that operate a phone number powered by
              Meridian to take customer orders.
            </li>
            <li>
              <strong>Customers</strong> — individuals who call or text a merchant&rsquo;s
              Meridian-powered number to place an order.
            </li>
          </ul>

          <h2>2. Acceptable use</h2>
          <p>You agree not to:</p>
          <ul>
            <li>Use the Services for any illegal purpose or in violation of any applicable law.</li>
            <li>
              Send unsolicited or harassing messages, attempt to impersonate another person, or
              interfere with another user&rsquo;s use of the Services.
            </li>
            <li>
              Probe, scan, or test the vulnerability of any system associated with the Services
              without our written permission.
            </li>
            <li>
              Attempt to reverse-engineer, decompile, or extract source code from any part of the
              Services, except to the extent expressly permitted by law.
            </li>
            <li>
              Use the Services to send spam, phishing messages, or any other content that violates
              applicable telecommunications law (including the TCPA, CAN-SPAM, or CASL).
            </li>
          </ul>

          <h2>3. SMS messaging</h2>
          <p>
            By providing your phone number and verbally consenting during a call (or by texting our
            number first), you agree to receive SMS messages from Meridian on behalf of the
            merchant related to your order. Typical messages include payment links, order
            confirmations, and order-ready notifications.
          </p>
          <p>
            Message frequency varies by activity and is typically one to three messages per order.
            Message and data rates may apply. You can opt out at any time by replying{' '}
            <strong>STOP</strong>. Reply <strong>HELP</strong> for assistance.
          </p>

          <h2>4. Orders and payments</h2>
          <p>
            All orders placed through the Services are between you and the merchant. Meridian acts
            as a technology intermediary; we do not sell food or goods directly. Payments are
            processed by the merchant&rsquo;s payment processor (typically Square, Toast, or Clover).
            We do not collect, store, or transmit full card numbers.
          </p>
          <p>
            Refunds, cancellations, and other order disputes must be resolved with the merchant
            directly. Meridian is not responsible for the quality, accuracy, or delivery of the
            goods or services provided by the merchant.
          </p>

          <h2>5. AI accuracy and order verification</h2>
          <p>
            Meridian uses automated speech recognition and large language models to interpret your
            order. These systems are not perfect and may occasionally misunderstand items,
            quantities, or special requests. <strong>Please verify your order</strong> with the
            merchant before payment if accuracy is critical. Meridian is not liable for order errors
            caused by speech recognition mistakes or AI misinterpretation.
          </p>

          <h2>6. Merchant accounts</h2>
          <p>
            Merchants who sign up for Meridian agree to the additional terms presented during
            account onboarding, including the agreement to (a) collect proper opt-in consent from
            customers before sending SMS, (b) honour opt-out requests, (c) comply with applicable
            telecommunications law, and (d) supply accurate menu, pricing, and tax information.
            Merchants are responsible for the legality of their orders, including age-restricted
            items where applicable.
          </p>

          <h2>7. Intellectual property</h2>
          <p>
            The Services, including all software, models, and content (other than user-submitted
            content), are owned by Meridian and licensed to you for use only under these Terms.
            Nothing in these Terms grants you any right in our trademarks, logos, or branding.
          </p>

          <h2>8. Service availability</h2>
          <p>
            We aim to keep the Services available 24/7 but make no uptime guarantee. We may suspend
            or discontinue any feature at any time, with or without notice. We are not liable for
            any loss caused by service interruption.
          </p>

          <h2>9. Disclaimer of warranties</h2>
          <p>
            <strong>
              THE SERVICES ARE PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; WITHOUT
              WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING IMPLIED WARRANTIES OF
              MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT. WE DO NOT
              WARRANT THAT THE SERVICES WILL BE UNINTERRUPTED, ERROR-FREE, OR FREE OF HARMFUL
              COMPONENTS.
            </strong>
          </p>

          <h2>10. Limitation of liability</h2>
          <p>
            <strong>
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, MERIDIAN&rsquo;S TOTAL LIABILITY FOR ANY CLAIM
              ARISING FROM OR RELATED TO THESE TERMS OR THE SERVICES SHALL NOT EXCEED THE AMOUNT YOU
              PAID US (IF ANY) IN THE TWELVE MONTHS PRECEDING THE EVENT GIVING RISE TO THE CLAIM, OR
              ONE HUNDRED U.S. DOLLARS, WHICHEVER IS GREATER. IN NO EVENT WILL WE BE LIABLE FOR ANY
              INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.
            </strong>
          </p>

          <h2>11. Indemnification</h2>
          <p>
            You agree to indemnify and hold Meridian harmless from any claim, damage, or expense
            (including reasonable legal fees) arising out of your violation of these Terms, your
            misuse of the Services, or your violation of any law or the rights of a third party.
          </p>

          <h2>12. Governing law and disputes</h2>
          <p>
            These Terms are governed by the laws of the State of {GOVERNING_STATE}, without regard
            to conflict-of-laws principles. Any dispute arising from these Terms or the Services
            will be resolved by binding arbitration on an individual basis, except that either
            party may seek injunctive relief in court for intellectual-property violations.
          </p>

          <h2>13. Changes to these Terms</h2>
          <p>
            We may update these Terms from time to time. When we do, we will post the updated
            version here and adjust the &ldquo;Effective&rdquo; date at the top. Material changes
            will be announced via email or in-app notice where reasonably feasible. Continued use
            of the Services after the change means you accept the updated Terms.
          </p>

          <h2>14. Contact</h2>
          <p>
            Legal questions: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
            <br />
            General support: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
          </p>
        </article>

        <footer className="mt-16 flex items-center justify-between border-t border-zinc-800/60 pt-8 text-sm text-zinc-500">
          <span>&copy; {new Date().getFullYear()} {LEGAL_ENTITY}. All rights reserved.</span>
          <a href="/privacy" className="hover:text-zinc-200">
            Privacy Policy
          </a>
        </footer>
      </main>
    </div>
  )
}
