import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Instagram,
  Facebook,
  Linkedin,
  Globe,
  MapPin,
  Clock,
  ImagePlus,
  RefreshCw,
  X,
  Check,
  Music2,
  Lock,
  MessageSquarePlus,
} from 'lucide-react'
import type { ContentPost } from '@/lib/content-demo-data'

interface PostReviewCardProps {
  post: ContentPost
  onApprove?: (scheduledAt?: string) => void
  onReject?: () => void
  onRegenerate?: (field: 'image' | 'copy' | 'all') => void
  disabled?: boolean
  readOnly?: boolean
}

interface PlatformMeta {
  icon: typeof Instagram
  label: string
  color: string
}

const PLATFORMS: Record<string, PlatformMeta> = {
  instagram: { icon: Instagram, label: 'Instagram', color: 'text-purple-400' },
  facebook: { icon: Facebook, label: 'Facebook', color: 'text-blue-400' },
  tiktok: { icon: Music2, label: 'TikTok', color: 'text-[#F5F5F7]' },
  linkedin: { icon: Linkedin, label: 'LinkedIn', color: 'text-blue-500' },
  google_business: { icon: MapPin, label: 'Google Business', color: 'text-green-400' },
  wordpress: { icon: Globe, label: 'WordPress', color: 'text-blue-400' },
}

export default function PostReviewCard({
  post,
  onApprove,
  onReject,
  onRegenerate,
  disabled = false,
  readOnly = false,
}: PostReviewCardProps) {
  const [showScheduler, setShowScheduler] = useState(false)
  const [scheduledDate, setScheduledDate] = useState('')

  const platform = PLATFORMS[post.platform] || { icon: Globe, label: post.platform, color: 'text-[#A1A1A8]' }
  const PlatformIcon = platform.icon
  const displayTitle = post.title || post.hook || '(untitled)'
  const displayBody = post.body || ''
  const hasPosData = post.pos_data_reference && Object.keys(post.pos_data_reference).length > 0

  function handleApprove() {
    if (!onApprove) return
    if (showScheduler && scheduledDate) {
      onApprove(new Date(scheduledDate).toISOString())
    } else {
      onApprove()
    }
  }

  return (
    <div className="card p-4 sm:p-5 group hover:border-[#1F1F23]/80 transition-colors">
      {/* Large preview image for readOnly/demo */}
      {readOnly && post.image_url && (
        <div className="mb-4">
          <img
            src={post.image_url}
            alt=""
            className="w-full aspect-square sm:aspect-[4/3] rounded-lg object-cover bg-[#1F1F23]"
          />
        </div>
      )}

      <div className="flex gap-4">
        {/* Thumbnail — compact view for non-readOnly */}
        {!readOnly && (
          post.image_url ? (
            <img
              src={post.image_url}
              alt=""
              className="w-20 h-20 rounded-lg object-cover flex-shrink-0 bg-[#1F1F23]"
            />
          ) : (
            <div className="w-20 h-20 rounded-lg bg-[#1F1F23] flex items-center justify-center flex-shrink-0">
              <PlatformIcon size={28} className={platform.color} />
            </div>
          )
        )}

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-1.5">
          {/* Platform label */}
          <div className="flex items-center gap-1.5">
            <PlatformIcon size={14} className={platform.color} />
            <span className="text-[11px] font-medium text-[#A1A1A8]">{platform.label}</span>
            {post.post_type === 'article' && (
              <span className="text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-1.5 py-0.5 rounded ml-1">
                ARTICLE
              </span>
            )}
          </div>

          {/* Title / Hook */}
          <p className="text-sm font-semibold text-[#F5F5F7]">{displayTitle}</p>

          {/* Body — full text in readOnly, clipped otherwise */}
          <p className={clsx(
            'text-xs text-[#A1A1A8] leading-relaxed',
            readOnly ? 'whitespace-pre-line' : 'line-clamp-2',
          )}>{displayBody}</p>

          {/* POS data badge + hashtags */}
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
            {hasPosData && (
              <span className="text-[10px] font-medium text-[#17C5B0] bg-[#17C5B0]/10 border border-[#17C5B0]/20 px-1.5 py-0.5 rounded">
                POS Data
              </span>
            )}
            {post.hashtags?.map(tag => (
              <span
                key={tag}
                className="text-[10px] text-[#A1A1A8]/60 bg-[#1F1F23] px-1.5 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
          </div>

          {/* CTA preview */}
          {readOnly && post.call_to_action && (
            <p className="text-[11px] text-[#1A8FD6] font-medium pt-1">{post.call_to_action}</p>
          )}
        </div>
      </div>

      {/* Action bar */}
      {readOnly ? (
        <div className="mt-4 pt-3 border-t border-[#1F1F23] space-y-3">
          <div className="flex items-center gap-2">
            <button
              disabled
              className="flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8]/50 bg-[#1F1F23] px-2.5 py-1.5 rounded-md cursor-not-allowed"
              title="Connect your POS to generate captions"
            >
              <Lock size={12} /> Generate Caption
            </button>
            <button
              disabled
              className="flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8]/50 bg-[#1F1F23] px-2.5 py-1.5 rounded-md cursor-not-allowed"
              title="Connect your POS to generate hashtags"
            >
              <Lock size={12} /> Generate Hashtags
            </button>
            <button
              disabled
              className="flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8]/50 bg-[#1F1F23] px-2.5 py-1.5 rounded-md cursor-not-allowed"
              title="Connect your accounts to publish"
            >
              <Lock size={12} /> Publish
            </button>
          </div>
          <div className="flex items-center justify-between">
            {post.status === 'published' && post.published_at && (
              <span className="text-[10px] text-[#A1A1A8]/50">
                Published {new Date(post.published_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            )}
            <p className="text-[10px] text-[#A1A1A8]/30 italic ml-auto">
              Example AI-generated ad — connect your POS to create your own
            </p>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-[#1F1F23]">
          {/* Left: regenerate actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onRegenerate?.('image')}
              disabled={disabled}
              className="flex items-center gap-1 text-[11px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] bg-[#1F1F23] hover:bg-[#1F1F23]/80 px-2.5 py-1.5 rounded-md transition-colors disabled:opacity-40"
            >
              <ImagePlus size={12} /> New Image
            </button>
            <button
              onClick={() => onRegenerate?.('copy')}
              disabled={disabled}
              className="flex items-center gap-1 text-[11px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] bg-[#1F1F23] hover:bg-[#1F1F23]/80 px-2.5 py-1.5 rounded-md transition-colors disabled:opacity-40"
            >
              <RefreshCw size={12} /> Rewrite
            </button>
          </div>

          {/* Right: approve/reject */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onReject?.()}
              disabled={disabled}
              className="flex items-center gap-1 text-[11px] font-medium text-[#A1A1A8] hover:text-red-400 bg-[#1F1F23] hover:bg-red-400/10 px-2.5 py-1.5 rounded-md transition-colors disabled:opacity-40"
            >
              <X size={12} /> Skip
            </button>

            {showScheduler ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="datetime-local"
                  value={scheduledDate}
                  onChange={e => setScheduledDate(e.target.value)}
                  className="text-[11px] bg-[#1F1F23] border border-[#1F1F23] text-[#F5F5F7] rounded-md px-2 py-1.5 focus:border-[#1A8FD6] focus:outline-none"
                />
                <button
                  onClick={handleApprove}
                  disabled={disabled || !scheduledDate}
                  className={clsx(
                    'flex items-center gap-1 text-[11px] font-semibold px-3 py-1.5 rounded-md transition-colors disabled:opacity-40',
                    'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90',
                  )}
                >
                  <Check size={12} /> Schedule
                </button>
                <button
                  onClick={() => setShowScheduler(false)}
                  className="text-[#A1A1A8] hover:text-[#F5F5F7] p-1"
                >
                  <X size={12} />
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={handleApprove}
                  disabled={disabled}
                  className="flex items-center gap-1 text-[11px] font-semibold bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#17C5B0]/90 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40"
                >
                  <Check size={12} /> Approve
                </button>
                <button
                  onClick={() => setShowScheduler(true)}
                  disabled={disabled}
                  className="p-1.5 text-[#A1A1A8] hover:text-[#1A8FD6] hover:bg-[#1A8FD6]/10 rounded-md transition-colors disabled:opacity-40"
                  title="Schedule for later"
                >
                  <Clock size={14} />
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
