/**Inner Swiper component — code-split via lazy import.**/
import { Swiper, SwiperSlide } from 'swiper/react'
import { Pagination } from 'swiper/modules'
import type { ReactNode } from 'react'

interface Props {
  insights: Array<{ id: string; [key: string]: unknown }>
  renderCard: (insight: { id: string; [key: string]: unknown }) => ReactNode
}

export default function SwiperCarousel({ insights, renderCard }: Props) {
  return (
    <Swiper
      modules={[Pagination]}
      spaceBetween={12}
      slidesPerView={1.15}
      breakpoints={{
        640: { slidesPerView: 1.5, spaceBetween: 16 },
        768: { slidesPerView: 2.2, spaceBetween: 16 },
        1024: { slidesPerView: 3, spaceBetween: 20 },
      }}
      pagination={{ clickable: true, dynamicBullets: true }}
      grabCursor
      className="!pb-8"
    >
      {insights.map(insight => (
        <SwiperSlide key={insight.id}>
          {renderCard(insight)}
        </SwiperSlide>
      ))}
    </Swiper>
  )
}
