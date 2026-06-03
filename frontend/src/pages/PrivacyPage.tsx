import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import SEO from '@/components/SEO'
import MeridianLogo from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'

const EASE = [0.16, 1, 0.3, 1] as const

// Single source of truth for the things a future you / lawyer will want to
// update. Edit these constants, do not search-and-replace through the body.
const LEGAL_ENTITY = 'Meridian'
const CONTACT_EMAIL = 'privacy@meridian.tips'
const SUPPORT_EMAIL = 'support@meridian.tips'
const EFFECTIVE_DATE = 'June 4, 2026'

export default function PrivacyPage() {
  const navigate = useNavigate()

  return (
    <div className="relative min-h-screen bg-zinc-950 text-zinc-100">
      <SEO
        title="Privacy Policy — Meridian"
        description="How Meridian collects, uses, and protects the information you share with our AI phone agent and POS analytics platform."
        path="/privacy"
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
          <h1 className="mt-2 text-4xl font-semibold tracking-tight md:text-5xl">Privacy Policy</h1>
          <p className="mt-4 text-sm text-zinc-500">Effective {EFFECTIVE_DATE}</p>
        </motion.div>

        <article className="prose prose-invert prose-zinc mt-12 max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-h2:mt-12 prose-h2:text-2xl prose-h3:mt-8 prose-h3:text-lg prose-p:text-zinc-300 prose-li:text-zinc-300 prose-strong:text-zinc-100 prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline">
          <p>
            {LEGAL_ENTITY} (&ldquo;<strong>Meridian</strong>,&rdquo; &ldquo;we,&rdquo; &ldquo;our&rdquo;) operates an AI-powered
            phone ordering and POS analytics platform for restaurants, cafes, and similar businesses.
            This Privacy Policy describes what we collect, how we use it, and the choices you have.
          </p>

          <h2>Information we collect</h2>
          <h3>From callers and texters</h3>
          <ul>
            <li>
              <strong>Phone number.</strong> When you call or text a merchant&rsquo;s Meridian-powered
              number, we receive your phone number from the caller-ID metadata provided by the
              telephone network (via our carrier, Twilio).
            </li>
            <li>
              <strong>Conversation content.</strong> Spoken words during the call are transcribed by
              our speech-to-text provider. SMS messages you send are stored as plain text. We use
              both to understand and fulfil your order.
            </li>
            <li>
              <strong>Order details.</strong> Items, quantities, modifications, name, pickup or
              delivery preference, and (for delivery) the address you provide.
            </li>
            <li>
              <strong>Payment information.</strong> When you complete a payment via a link we send,
              your card information is collected and processed directly by Square. Meridian never
              sees or stores your full card number; we only receive payment confirmation (success or
              failure) and the last four digits of the card used.
            </li>
          </ul>

          <h3>From merchant operators</h3>
          <p>
            Business account details (legal name, address, EIN, POS access tokens, menu items, voice
            preferences) provided during onboarding. POS access tokens are stored encrypted at rest.
          </p>

          <h3>From your device, automatically</h3>
          <p>
            Standard web logs (IP address, browser, pages viewed) when you visit meridian.tips. We
            use first-party analytics to understand site usage; we do not run third-party
            advertising trackers.
          </p>

          <h2>How we use it</h2>
          <ul>
            <li>Take your order and route it to the merchant&rsquo;s point-of-sale system.</li>
            <li>Send you a payment link or order-status text (only when you have asked us to).</li>
            <li>Improve the AI assistant&rsquo;s accuracy by reviewing transcripts in aggregate.</li>
            <li>Detect fraud, abuse, and service outages.</li>
            <li>Meet legal and tax obligations on behalf of the merchant.</li>
          </ul>

          <h2>SMS messaging and consent</h2>
          <p>
            When you place an order through our AI phone agent, you may verbally consent to receive
            a one-time SMS containing a payment link to complete your order, and follow-up texts
            related to that order (such as &ldquo;order ready&rdquo; notifications). The frequency is
            typically one to three messages per order.
          </p>
          <p>
            You can opt out at any time by replying <strong>STOP</strong> to any of our messages.
            Reply <strong>HELP</strong> for assistance, or contact{' '}
            <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>. Message and data rates may
            apply.
          </p>

          <h3>No SMS data sharing</h3>
          <p>
            <strong>
              Information related to SMS messaging — phone numbers, opt-in consent records, message
              content, and conversation metadata — is collected solely to provide the service and is
              not shared with third parties for marketing, promotional, or any other purpose. The
              only third party that processes SMS messages on our behalf is our carrier provider
              (Twilio), and they do so under their own terms.
            </strong>
          </p>

          <h2>How we share information</h2>
          <p>We share information only with the parties needed to deliver the service:</p>
          <ul>
            <li>
              <strong>The merchant</strong> whose number you called or texted (your order details
              and phone number, so they can fulfil the order).
            </li>
            <li>
              <strong>Twilio</strong> for telephony and SMS delivery.
            </li>
            <li>
              <strong>Square</strong>, Clover, Toast, or the merchant&rsquo;s configured POS for
              order routing and payment processing.
            </li>
            <li>
              <strong>Our cloud infrastructure providers</strong> (Railway, Supabase) for storage
              and compute.
            </li>
            <li>
              <strong>Law enforcement</strong> when required by a valid legal request.
            </li>
          </ul>
          <p>
            We do not sell your personal information. We do not share your phone number or SMS
            consent with any third party for marketing purposes.
          </p>

          <h2>How long we keep it</h2>
          <ul>
            <li>Call transcripts: 12 months, then deleted.</li>
            <li>SMS message logs: 12 months, then deleted.</li>
            <li>Order records: 7 years (tax compliance).</li>
            <li>Opt-out records: retained indefinitely so we do not contact you again.</li>
          </ul>

          <h2>Your choices</h2>
          <ul>
            <li>
              <strong>Opt out of SMS</strong> by replying STOP to any message.
            </li>
            <li>
              <strong>Request a copy</strong> of the information we hold about you by emailing{' '}
              <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
            </li>
            <li>
              <strong>Request deletion</strong> of your information (subject to legal retention
              requirements) by emailing the same address.
            </li>
            <li>
              <strong>California residents</strong> have additional rights under the CCPA, including
              the right to know what we collect and the right to opt out of any &ldquo;sale&rdquo; of
              personal information. We do not sell personal information.
            </li>
          </ul>

          <h2>Security</h2>
          <p>
            We use TLS for all data in transit, encrypt POS access tokens at rest, and restrict
            access to production systems to a small number of authorised personnel. No system is
            perfectly secure; if you believe your information has been compromised, contact us
            immediately at <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
          </p>

          <h2>Children</h2>
          <p>
            Meridian is intended for use by adults placing orders with participating merchants. We
            do not knowingly collect information from children under 13. If you believe a child has
            provided information to us, contact{' '}
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> and we will delete it.
          </p>

          <h2>Changes to this policy</h2>
          <p>
            We may update this policy. If we make material changes, we will post the updated version
            here and adjust the &ldquo;Effective&rdquo; date at the top. Continued use of the service
            after a change means you accept the updated policy.
          </p>

          <h2>Contact</h2>
          <p>
            Privacy questions: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
            <br />
            General support: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
          </p>
        </article>

        <footer className="mt-16 flex items-center justify-between border-t border-zinc-800/60 pt-8 text-sm text-zinc-500">
          <span>&copy; {new Date().getFullYear()} {LEGAL_ENTITY}. All rights reserved.</span>
          <a href="/terms" className="hover:text-zinc-200">
            Terms of Service
          </a>
        </footer>
      </main>
    </div>
  )
}
