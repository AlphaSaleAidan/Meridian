import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import type { ContentJob } from '@/lib/content-demo-data'

interface ActiveJobsBannerProps {
  jobs: ContentJob[]
}

export default function ActiveJobsBanner({ jobs }: ActiveJobsBannerProps) {
  if (jobs.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 px-4 py-3 flex items-center gap-3"
    >
      <Loader2 size={18} className="text-[#1A8FD6] animate-spin flex-shrink-0" />
      <p className="text-sm text-[#F5F5F7]">
        Generating content...{' '}
        <span className="text-[#A1A1A8] font-mono">
          {jobs.length} job{jobs.length !== 1 ? 's' : ''} running
        </span>
      </p>
    </motion.div>
  )
}
