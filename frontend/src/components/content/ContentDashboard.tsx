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
import type { ContentPost } from '@/lib/content-demo-data'

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
              onClick={() => setUpsellOpen(true)}
              className="flex items-center gap-1.5 text-[11px] font-semibold bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 px-3 py-2 rounded-lg transition-colors"
            >
              <CalendarPlus size={14} /> Generate Calendar
            </button>
          )}
        </div>
      </div>

      {/* Active jobs banner — never shown in demo */}
      {!demo && data?.activeJobs && <ActiveJobsBanner jobs={data.activeJobs} />}

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
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
            change={stats.publishedCount > 0 ? `${stats.publishedCount} this month` : undefined}
            changeType="positive"
          />
          <StatCard
            label="Keywords Tracking"
            value={String(stats.keywordsTracked)}
            icon={Search}
            iconColor="text-amber-400"
          />
          <StatCard
            label="Avg Rank"
            value={stats.avgRank > 0 ? `#${stats.avgRank}` : '--'}
            icon={BarChart3}
            iconColor="text-purple-400"
          />
        </div>
      )}

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

      {/* Demo upsell banner */}
      {demo && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card p-6 border-[#1A8FD6]/20 bg-gradient-to-br from-[#1A8FD6]/5 to-transparent"
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="p-3 rounded-xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20">
              <Sparkles size={24} className="text-[#1A8FD6]" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-[#F5F5F7]">
                Upgrade to Content Creation
              </h3>
              <p className="text-sm text-[#A1A1A8] mt-1">
                AI-powered social posts, SEO articles, and rank tracking — all driven by your real POS data.
                Starting at {isCanadaPath() ? 'CA$67' : '$49'}/mo.
              </p>
            </div>
            <button className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#1A8FD6] text-white text-sm font-medium hover:bg-[#1A8FD6]/90 transition-colors flex-shrink-0">
              View Plans <ArrowRight size={14} />
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
          <RankingsTable rankings={data.rankings.slice(0, 8)} />
        </section>
      )}

      {/* Upsell modal — real mode only */}
      {!demo && <ContentUpsellModal open={upsellOpen} onClose={() => setUpsellOpen(false)} />}
    </motion.div>
  )
}
