import { Link } from 'react-router-dom'
import { ArrowRight, Clock, TrendingUp, Camera, CreditCard } from 'lucide-react'
import SEO from '@/components/SEO'

interface ArticleCard {
  slug: string
  title: string
  description: string
  keyword: string
  readTime: string
  date: string
  icon: React.ReactNode
  category: string
}

const articles: ArticleCard[] = [
  {
    slug: 'how-to-know-if-restaurant-is-profitable',
    title: 'How to Know If Your Restaurant is Actually Profitable',
    description: 'Most restaurant owners track revenue but miss true profitability. Learn the 7 metrics that actually matter — and how POS analytics reveals them automatically.',
    keyword: 'restaurant profitability analytics',
    readTime: '8 min',
    date: 'May 22, 2026',
    icon: <TrendingUp className="w-5 h-5" />,
    category: 'Restaurant Analytics',
  },
  {
    slug: 'restaurant-foot-traffic-analytics-guide',
    title: 'The Complete Guide to Restaurant Foot Traffic Analytics in 2026',
    description: 'Learn how modern foot traffic analytics works for restaurants and retail — from camera-based counting to POS correlation. No expensive hardware required.',
    keyword: 'restaurant foot traffic analytics',
    readTime: '9 min',
    date: 'May 22, 2026',
    icon: <Camera className="w-5 h-5" />,
    category: 'Foot Traffic',
  },
  {
    slug: 'square-pos-analytics-what-it-tells-you',
    title: 'Square POS Analytics: What Square Tells You (And What It Doesn\'t)',
    description: 'Square gives you basic sales reports. Here\'s what\'s missing — and how to get real analytics from your Square data.',
    keyword: 'Square POS analytics',
    readTime: '7 min',
    date: 'Coming Week 2',
    icon: <CreditCard className="w-5 h-5" />,
    category: 'POS Integrations',
  },
]

export default function BlogIndexPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      <SEO
        title="Meridian Blog — POS Analytics Insights for Restaurants & Retail"
        description="Expert guides on POS analytics, restaurant profitability, foot traffic tracking, and AI-powered business intelligence. Practical insights for restaurant and retail operators."
        path="/blog"
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
        <div className="mb-4">
          <Link to="/" className="text-[#A1A1A8] hover:text-[#F5F5F7] text-sm transition-colors">
            Meridian
          </Link>
          <span className="text-[#A1A1A8] mx-2">/</span>
          <span className="text-[#F5F5F7] text-sm">Blog</span>
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold text-[#F5F5F7] mb-4">
          POS Analytics Insights
        </h1>
        <p className="text-lg text-[#A1A1A8] mb-12 max-w-2xl">
          Practical guides on restaurant analytics, POS data, foot traffic tracking, and AI-powered
          business intelligence. Written for operators, not analysts.
        </p>

        <div className="grid gap-6">
          {articles.map((article) => {
            const isPublished = !article.date.startsWith('Coming')
            return (
              <article key={article.slug}>
                {isPublished ? (
                  <Link
                    to={`/blog/${article.slug}`}
                    className="block bg-[#111113] border border-[#1F1F23] rounded-xl p-6 sm:p-8 hover:border-[#17C5B0]/40 transition-all group"
                  >
                    <ArticleContent article={article} isPublished />
                  </Link>
                ) : (
                  <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 sm:p-8 opacity-60">
                    <ArticleContent article={article} isPublished={false} />
                  </div>
                )}
              </article>
            )
          })}
        </div>

        <div className="mt-16 border-t border-[#1F1F23] pt-12">
          <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">Explore by Topic</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Link to="/for/restaurants" className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 hover:border-[#17C5B0]/40 transition-colors">
              <span className="text-[#F5F5F7] font-medium">Restaurant Analytics</span>
              <p className="text-sm text-[#A1A1A8] mt-1">Revenue, margins, menu engineering</p>
            </Link>
            <Link to="/for/coffee-shops" className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 hover:border-[#17C5B0]/40 transition-colors">
              <span className="text-[#F5F5F7] font-medium">Coffee Shop Analytics</span>
              <p className="text-sm text-[#A1A1A8] mt-1">Peak hours, inventory, loyalty</p>
            </Link>
            <Link to="/what-is-pos-analytics" className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 hover:border-[#17C5B0]/40 transition-colors">
              <span className="text-[#F5F5F7] font-medium">What Is POS Analytics?</span>
              <p className="text-sm text-[#A1A1A8] mt-1">The definitive guide</p>
            </Link>
            <Link to="/guides" className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 hover:border-[#17C5B0]/40 transition-colors">
              <span className="text-[#F5F5F7] font-medium">Guides for Operators</span>
              <p className="text-sm text-[#A1A1A8] mt-1">Food cost, pricing, staffing, forecasting</p>
            </Link>
            <Link to="/best-restaurant-analytics-software" className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 hover:border-[#17C5B0]/40 transition-colors">
              <span className="text-[#F5F5F7] font-medium">Best Analytics Software</span>
              <p className="text-sm text-[#A1A1A8] mt-1">2026 comparison guide</p>
            </Link>
            <Link to="/faq" className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4 hover:border-[#17C5B0]/40 transition-colors">
              <span className="text-[#F5F5F7] font-medium">FAQ</span>
              <p className="text-sm text-[#A1A1A8] mt-1">40+ questions answered</p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function ArticleContent({ article, isPublished }: { article: ArticleCard; isPublished: boolean }) {
  return (
    <>
      <div className="flex items-center gap-3 mb-3">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#17C5B0] bg-[#17C5B0]/10 px-2.5 py-1 rounded-full">
          {article.icon}
          {article.category}
        </span>
        <span className="text-xs text-[#A1A1A8] flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {article.readTime}
        </span>
      </div>
      <h2 className="text-xl sm:text-2xl font-bold text-[#F5F5F7] mb-2 group-hover:text-[#17C5B0] transition-colors">
        {article.title}
      </h2>
      <p className="text-[#A1A1A8] mb-4">{article.description}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs text-[#A1A1A8]">{article.date}</span>
        {isPublished && (
          <span className="text-[#17C5B0] text-sm font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
            Read article <ArrowRight className="w-4 h-4" />
          </span>
        )}
        {!isPublished && (
          <span className="text-[#A1A1A8] text-sm">Coming soon</span>
        )}
      </div>
    </>
  )
}
