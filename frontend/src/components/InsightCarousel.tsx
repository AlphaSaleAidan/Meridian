/**Touch-swipeable insight carousel powered by Swiper.**/
import { lazy, Suspense, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface Insight {
  id: string
  [key: string]: unknown
}

interface InsightCarouselProps {
  insights: Insight[]
  className?: string
  renderCard: (insight: Insight) => ReactNode
}

const SwiperCarousel = lazy(() => import('./SwiperCarousel'))

function Fallback({ insights, renderCard }: Pick<InsightCarouselProps, 'insights' | 'renderCard'>) {
  return (
    <div className="flex gap-3 overflow-x-auto no-scrollbar">
      {insights.slice(0, 3).map(i => (
        <div key={i.id} className="flex-shrink-0 w-[85%] sm:w-[60%] lg:w-[32%]">
          {renderCard(i)}
        </div>
      ))}
    </div>
  )
}

export default function InsightCarousel({ insights, className, renderCard }: InsightCarouselProps) {
  if (!insights.length) return null

  return (
    <div className={cn('insight-carousel', className)}>
      <Suspense fallback={<Fallback insights={insights} renderCard={renderCard} />}>
        <SwiperCarousel insights={insights} renderCard={renderCard} />
      </Suspense>
    </div>
  )
}
