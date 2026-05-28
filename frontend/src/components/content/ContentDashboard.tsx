import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Sparkles,
  FileText,
  Search,
  BarChart3,
  CalendarPlus,
  Clock,
  Settings,
  Lock,
  Zap,
  ArrowRight,
  Instagram,
  Facebook,
  MapPin,
  Music2,
  Linkedin,
  Link2,
  Coins,
  Film,
} from 'lucide-react'
import StatCard from '@/components/StatCard'
import { useContentDashboard } from '@/hooks/useContentDashboard'
import { usePostActions } from '@/hooks/usePostActions'
import { useAuth } from '@/lib/auth'
import { isCanadaPath } from '@/lib/demo-context'
import ActiveJobsBanner from './ActiveJobsBanner'
import PostReviewCard from './PostReviewCard'
import RankingsTable from './RankingsTable'
import ContentUpsellModal from './ContentUpsellModal'
import VideoStudioTab from './VideoStudioTab'
import type { ContentPost } from '@/lib/content-demo-data'

type ContentTab = 'content' | 'video'

export default function ContentDashboard() {
  const { data, loading, error, refetch } = useContentDashboard()
  const { approvePost, rejectPost, regeneratePost, isPending } = usePostActions(refetch)
  const { org } = useAuth()
  const orgId = org?.org_id || 'demo'
  const demo = orgId === 'demo'
  const navigate = useNavigate()
  const location = useLocation()
  const basePath = location.pathname.replace(/\/content$/, '')

  const [upsellOpen, setUpsellOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<ContentTab>('content')

  // Derived stats
  const stats = useMemo(() => {
    if (!data) return null

    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

    const postsThisMonth = data.posts.filter(p => new Date(p.created_at) >= startOfMonth).length
    const publishedCount = data.posts.filter(p => p.status === 'published').length
    const keywordsTracked = data.rankings.length
    const avgRank =
      data.rankings.length > 0
        ? Math.round(data.rankings.reduce((sum, r) => sum + r.rank_position, 0) / data.rankings.length)
        : 0

    return { postsThisMonth, publishedCount, keywordsTracked, avgRank }
  }, [data])

  const needsReviewPosts = useMemo<ContentPost[]>(() => {
    if (!data) return []
    return data.posts.filter(p => p.status === 'needs_review').slice(0, 5)
  }, [data])

  const scheduledPosts = useMemo<ContentPost[]>(() => {
    if (!data) return []
    return data.posts
      .filter(p => p.status === 'scheduled' && p.scheduled_at)
      .sort((a, b) => new Date(a.scheduled_at!).getTime() - new Date(b.scheduled_at!).getTime())
      .slice(0, 5)
  }, [data])

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-6 h-6 rounded-md bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#1A8FD6] font-bold text-[10px]">M</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-[#F5F5F7]">Content</h1>
        <div className="card p-6 text-center space-y-3">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={refetch}
            className="text-sm font-medium text-[#1A8FD6] hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Content</h1>
            <p className="text-sm text-[#A1A1A8] mt-0.5">
              {data?.brand ? data.brand.business_name : 'AI-powered content for your business'}
            </p>
          </div>
          {demo && (
            <span className="text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded self-start mt-1">
              DEMO
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!demo && (
            <button
              onClick={() => navigate(basePath + '/content/settings')}
              className="flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] bg-[#1F1F23] hover:bg-[#1F1F23]/80 px-3 py-2 rounded-lg transition-colors"
            >
              <Settings size={14} /> Settings
            </button>
          )}
          <button
            onClick={() => setUpsellOpen(true)}
            className="flex items-center gap-1.5 text-[11px] font-semibold bg-amber-500 text-[#0A0A0B] hover:bg-amber-400 px-3 py-2 rounded-lg transition-colors"
          >
            <Coins size={14} /> {demo ? 'Buy Credits' : 'Credits'}
          </button>
          {demo ? (
            <button
              disabled
              className="flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8]/50 bg-[#1F1F23] px-3 py-2 rounded-lg cursor-not-allowed"
              title="Connect your POS to generate content"
            >
              <Lock size={14} /> Generate Calendar
            </button>
          ) : (
            <button
              className="flex items-center gap-1.5 text-[11px] font-semibold bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 px-3 py-2 rounded-lg transition-colors"
            >
              <CalendarPlus size={14} /> Generate Calendar
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[#1F1F23] -mb-2">
        {([
          { id: 'content' as const, label: 'Content', icon: FileText },
          { id: 'video' as const, label: 'Video Studio', icon: Film },
        ]).map(t => {
          const Icon = t.icon
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-[11px] font-medium border-b-2 transition-colors -mb-px ${
                activeTab === t.id
                  ? 'border-[#1A8FD6] text-[#F5F5F7]'
                  : 'border-transparent text-[#A1A1A8] hover:text-[#F5F5F7]'
              }`}
            >
              <Icon size={13} />
              {t.label}
              {t.id === 'video' && (
                <span className="text-[8px] font-bold text-purple-400 bg-purple-500/10 px-1 py-0.5 rounded leading-none">
                  NEW
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Video Studio Tab */}
      {activeTab === 'video' && (
        <VideoStudioTab isDemo={demo} creditBalance={data?.credits?.balance ?? 0} merchantId={orgId} brand={data?.brand ?? null} />
      )}

      {/* Active jobs banner — never shown in demo */}
      {activeTab === 'content' && !demo && data?.activeJobs && <ActiveJobsBanner jobs={data.activeJobs} />}

      {/* Stat cards */}
      {activeTab === 'content' && stats && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <StatCard
            label="Credits"
            value={String(data?.credits?.balance ?? 0)}
            icon={Coins}
            iconColor="text-amber-400"
            change={demo ? '500 free on signup' : undefined}
            changeType="positive"
          />
          <StatCard
            label="Posts Created"
            value={String(stats.postsThisMonth)}
            icon={FileText}
            iconColor="text-[#1A8FD6]"
          />
          <StatCard
            label="Published"
            value={String(stats.publishedCount)}
            icon={Sparkles}
            iconColor="text-[#17C5B0]"
          />
          <StatCard
            label="Keywords Tracking"
            value={String(stats.keywordsTracked)}
            icon={Search}
            iconColor="text-purple-400"
          />
          <StatCard
            label="Avg Rank"
            value={stats.avgRank > 0 ? `#${stats.avgRank}` : '--'}
            icon={BarChart3}
            iconColor="text-[#1A8FD6]"
          />
        </div>
      )}

      {activeTab === 'content' && <>
      {/* Content Creation — the main showcase */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Content Creation</h2>
          {demo && (
            <span className="text-[10px] text-[#A1A1A8]/40 font-mono">
              AI-generated from POS data
            </span>
          )}
        </div>

        {data?.posts && data.posts.length > 0 ? (
          <div className="space-y-3">
            {data.posts.map(post => (
              <PostReviewCard
                key={post.id}
                post={post}
                onApprove={demo ? undefined : (scheduledAt) => approvePost(post.id, scheduledAt)}
                onReject={demo ? undefined : () => rejectPost(post.id)}
                onRegenerate={demo ? undefined : (field) => regeneratePost(post.id, field)}
                disabled={isPending}
                readOnly={demo}
              />
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center">
            <Sparkles size={32} className="text-[#A1A1A8]/30 mx-auto mb-3" />
            <p className="text-sm text-[#A1A1A8]">No content yet. Generate a calendar to get started.</p>
          </div>
        )}

        {/* Demo CTA */}
        {demo && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-4 p-4 rounded-lg border border-dashed border-[#1A8FD6]/20 bg-[#1A8FD6]/5 text-center"
          >
            <p className="text-sm text-[#A1A1A8]">
              <span className="text-[#1A8FD6] font-medium">Example ad</span> generated from demo POS data.
              Connect your real POS system to create content tailored to your actual best sellers.
            </p>
          </motion.div>
        )}
      </section>

      {/* How It Works — demo only */}
      {demo && (
        <section>
          <h2 className="text-sm font-semibold text-[#F5F5F7] mb-3">How It Works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { icon: BarChart3, title: 'POS Data', desc: 'We analyze your top sellers, peak hours, and revenue trends' },
              { icon: Sparkles, title: 'AI Writes Copy', desc: 'Claude generates posts that reference your real business data' },
              { icon: Zap, title: 'Auto-Publish', desc: 'Schedule or auto-post to Instagram, Facebook, and Google' },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="card p-4 space-y-2">
                <Icon size={18} className="text-[#1A8FD6]" />
                <p className="text-sm font-medium text-[#F5F5F7]">{title}</p>
                <p className="text-xs text-[#A1A1A8]">{desc}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Connect Social Accounts — demo only */}
      {demo && (
        <section>
          <h2 className="text-sm font-semibold text-[#F5F5F7] mb-3">Connect Your Accounts</h2>
          <p className="text-xs text-[#A1A1A8] mb-3 max-w-xl">
            Link your social media accounts so Meridian can auto-publish content directly.
            We never post without your approval unless you enable auto-publish.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {[
              { icon: Instagram, label: 'Instagram', color: 'text-purple-400', borderColor: 'border-purple-500/20 hover:border-purple-500/40' },
              { icon: Facebook, label: 'Facebook', color: 'text-blue-400', borderColor: 'border-blue-500/20 hover:border-blue-500/40' },
              { icon: Music2, label: 'TikTok', color: 'text-[#F5F5F7]', borderColor: 'border-[#1F1F23] hover:border-[#F5F5F7]/20' },
              { icon: Linkedin, label: 'LinkedIn', color: 'text-blue-500', borderColor: 'border-blue-600/20 hover:border-blue-600/40' },
              { icon: MapPin, label: 'Google Business', color: 'text-green-400', borderColor: 'border-green-500/20 hover:border-green-500/40' },
            ].map(({ icon: Icon, label, color, borderColor }) => (
              <button
                key={label}
                disabled
                className={`card p-3 flex flex-col items-center gap-2 border ${borderColor} cursor-not-allowed opacity-60 transition-colors`}
              >
                <Icon size={20} className={color} />
                <span className="text-[10px] font-medium text-[#A1A1A8]">{label}</span>
                <span className="flex items-center gap-1 text-[9px] text-[#A1A1A8]/40">
                  <Link2 size={9} /> Connect
                </span>
              </button>
            ))}
          </div>
          <p className="text-[10px] text-[#A1A1A8]/30 mt-2 italic">
            Sign up to connect your social accounts and start publishing
          </p>
        </section>
      )}

      {/* Demo upsell banner */}
      {demo && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card p-6 border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent"
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <Coins size={24} className="text-amber-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-[#F5F5F7]">
                500 Free Credits on Signup
              </h3>
              <p className="text-sm text-[#A1A1A8] mt-1">
                Every account gets 500 credits free — enough for 5 social posts, 2 SEO articles, or generate video ads.
                Need more? Credits start at {isCanadaPath() ? 'CA$2.75' : '$2'} for 2,000.
              </p>
            </div>
            <button
              onClick={() => setUpsellOpen(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-amber-500 text-[#0A0A0B] text-sm font-semibold hover:bg-amber-400 transition-colors flex-shrink-0"
            >
              <Coins size={14} /> Buy Credits
            </button>
          </div>
        </motion.div>
      )}

      {/* Needs Review — real mode only */}
      {!demo && needsReviewPosts.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-[#F5F5F7] mb-3">Needs Your Review</h2>
          <div className="space-y-3">
            {needsReviewPosts.map(post => (
              <PostReviewCard
                key={post.id}
                post={post}
                onApprove={(scheduledAt) => approvePost(post.id, scheduledAt)}
                onReject={() => rejectPost(post.id)}
                onRegenerate={(field) => regeneratePost(post.id, field)}
                disabled={isPending}
              />
            ))}
          </div>
        </section>
      )}

      {/* Scheduled — real mode only */}
      {!demo && scheduledPosts.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-[#F5F5F7] mb-3">Scheduled</h2>
          <div className="space-y-2">
            {scheduledPosts.map(post => (
              <div
                key={post.id}
                className="card p-3 sm:p-4 flex items-center gap-3"
              >
                <Clock size={14} className="text-[#1A8FD6] flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[#F5F5F7] truncate">
                    {post.title || post.hook || '(untitled)'}
                  </p>
                  <p className="text-[11px] text-[#A1A1A8]">
                    {post.platform} &middot;{' '}
                    {post.scheduled_at
                      ? new Date(post.scheduled_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: 'numeric',
                          minute: '2-digit',
                        })
                      : 'pending'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Rankings */}
      {data?.rankings && data.rankings.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-[#F5F5F7] mb-3">SEO Rankings</h2>

          {/* SEO explainer — demo only */}
          {demo && (
            <div className="space-y-3 mb-4">
              <p className="text-xs text-[#A1A1A8] leading-relaxed max-w-2xl">
                Meridian monitors your Google rankings daily and tracks when AI platforms
                like ChatGPT, Claude, and Perplexity cite your business in answers.
                Content we generate is optimized for these keywords automatically.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="card p-3.5 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Search size={14} className="text-amber-400" />
                    <span className="text-xs font-semibold text-[#F5F5F7]">Keyword Tracking</span>
                  </div>
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                    We track your most valuable search terms daily — your position,
                    movement, and which competitors rank above you.
                  </p>
                </div>
                <div className="card p-3.5 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} className="text-[#1A8FD6]" />
                    <span className="text-xs font-semibold text-[#F5F5F7]">AI Citations</span>
                  </div>
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                    When someone asks ChatGPT "best coffee shop near me" and it
                    recommends you — we track that. AI answers are the new search results.
                  </p>
                </div>
                <div className="card p-3.5 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <FileText size={14} className="text-[#17C5B0]" />
                    <span className="text-xs font-semibold text-[#F5F5F7]">Content → Rankings</span>
                  </div>
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                    Every blog post and article we generate targets your tracked keywords,
                    building authority so you rank higher on Google and in AI answers.
                  </p>
                </div>
              </div>
            </div>
          )}

          <RankingsTable rankings={data.rankings.slice(0, 8)} />

          {/* AI citation explainer — demo only */}
          {demo && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-3 p-3.5 rounded-lg border border-[#1F1F23] bg-[#131316]/50"
            >
              <div className="flex items-start gap-2.5">
                <div className="p-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 flex-shrink-0 mt-0.5">
                  <BarChart3 size={12} className="text-amber-400" />
                </div>
                <div className="space-y-1">
                  <p className="text-[11px] font-medium text-[#F5F5F7]">
                    Why AI Citations matter
                  </p>
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                    40% of consumers now use AI assistants to find local businesses.
                    When ChatGPT or Perplexity recommends your shop by name, that's a
                    direct referral you can't get from traditional SEO alone. Meridian's
                    content engine writes articles structured so AI models learn about
                    your business and cite you in their answers.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </section>
      )}

      </>}

      {/* Credit purchase modal */}
      <ContentUpsellModal open={upsellOpen} onClose={() => setUpsellOpen(false)} creditBalance={data?.credits?.balance ?? 0} />
    </motion.div>
  )
}
