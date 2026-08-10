import ScrollReveal from '@/components/landing/ScrollReveal'
import { useAutoplayFrameFilm } from '@/hooks/useAutoplayFrameFilm'

/**
 * The plain-English explainer, sitting under the hero as the first scroll reward.
 *
 * It plays on scroll exactly like the Captains cut further down the page — the sound
 * rules live in useAutoplayFrameFilm and are shared doctrine with useAutoplayFilm.
 *
 * Unlike Captains this is not an mp4 but a self-contained HTML film, so it runs in a
 * same-origin iframe: ?embed=1 strips its standalone page furniture down to the picture
 * and its transport, and ?theme=dark pins it to this page rather than letting it follow
 * each visitor's OS setting.
 */
const FILM_SRC = '/film/index.html?theme=dark&embed=1'

/** Canada's landing page runs a different accent, so it is passed in rather than fixed. */
export default function ExplainerFilm({ accent = '#0066FF' }: { accent?: string }) {
  const { holderRef, frameRef, mounted, muted, unmute, onFrameLoad, startManually, reduced } =
    useAutoplayFrameFilm()

  return (
    <section className="py-24 border-t border-[#1F1F23]/40 relative overflow-hidden">
      <div className="max-w-content mx-auto px-6">
        <ScrollReveal className="text-center mb-12 relative">
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow"
            style={{ width: 420, height: 420, opacity: 0.07, background: `radial-gradient(circle, ${accent} 0%, transparent 70%)` }}
          />
          <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight relative">
            See it in{' '}
            <em className="font-serif italic font-normal" style={{ color: accent }}>sixty-eight seconds</em>
          </h2>
          <p className="mt-4 text-[#A1A1A8] max-w-md mx-auto text-[15px] leading-relaxed relative">
            Plain English, hand-drawn. Every screen in it is the real product.
          </p>
        </ScrollReveal>

        <ScrollReveal className="relative max-w-4xl mx-auto" delay={0.1}>
          <div className="relative rounded-xl border border-[#1F1F23] bg-[#111113] shadow-2xl shadow-black/50 p-2">
            {/* Sized in index.css (.explainer-frame): the film is 16:9 + a 72px
                transport on desktop, but below 720px of frame width it restacks to
                its 4:5 mobile layout — the box has to follow or the film crops. */}
            <div ref={holderRef} className="relative w-full explainer-frame">
              {mounted && (
                <iframe
                  ref={frameRef}
                  src={FILM_SRC}
                  title="Meridian explainer film"
                  allow="autoplay"
                  onLoad={onFrameLoad}
                  className="absolute inset-0 w-full h-full border-0 block rounded-lg"
                />
              )}

              {/* The poster holds the space until the frame is in, so the section never
                  jumps, and it is the film's own opening frame so the swap is invisible. */}
              {!mounted && (
                <img
                  src="/media/explainer-poster.jpg"
                  alt="Opening frame: four drawings labelled the POS system, the phone, the front door and the leaks, beside the words Four things happen at once."
                  width={1600}
                  height={900}
                  className="absolute inset-0 m-auto w-full aspect-video rounded-lg block object-cover"
                />
              )}

              {/* Reduced motion: nothing started itself, so offer the normal way in. */}
              {reduced && !mounted && (
                <button
                  type="button"
                  onClick={startManually}
                  aria-label="Play the explainer film, 68 seconds"
                  className="absolute inset-0 flex items-center justify-center group"
                >
                  <span className="flex items-center justify-center w-[68px] h-[68px] md:w-20 md:h-20 rounded-full border border-white/15 bg-[#0A0A0B]/70 backdrop-blur-sm transition-transform duration-200 ease-out group-hover:scale-[1.06] motion-reduce:transform-none">
                    {/* nudged right ~2px: a triangle's optical centre sits left of its box */}
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" className="text-[#F5F5F7] translate-x-[2px]" aria-hidden="true">
                      <path d="M8 5.2v13.6a.7.7 0 0 0 1.07.6l10.6-6.8a.7.7 0 0 0 0-1.2L9.07 4.6A.7.7 0 0 0 8 5.2Z" />
                    </svg>
                  </span>
                </button>
              )}

              {/* Same control, same words and position as the Captains film above. */}
              {mounted && muted && (
                <button
                  type="button"
                  onClick={unmute}
                  className="absolute top-3 right-3 flex items-center gap-2 rounded-full border border-[#1F1F23] bg-[#0A0A0B]/80 px-3.5 py-2 text-[12px] font-medium text-[#F5F5F7] backdrop-blur transition-colors duration-200 hover:border-[#2A2A30]"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M11 5 6 9H2v6h4l5 4zM23 9l-6 6M17 9l6 6" />
                  </svg>
                  Unmute
                </button>
              )}
            </div>
          </div>

          <div
            className="absolute -bottom-16 left-1/2 -translate-x-1/2 w-[70%] h-32 opacity-[0.06] blur-[80px] rounded-full pointer-events-none"
            style={{ backgroundColor: accent }}
          />
        </ScrollReveal>
      </div>
    </section>
  )
}
