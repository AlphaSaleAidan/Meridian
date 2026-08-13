import { GraduationCap } from 'lucide-react'
import PlaybookViewer from '@/components/training/PlaybookViewer'
import ComplianceGuidesCard from '@/components/training/ComplianceGuidesCard'
import TrainingCourse from '@/components/training/TrainingCourse'
import { RegionOrientationCard } from '@/components/training/RegionOrientationCard'
import DemoCallCard from '@/components/phone/DemoCallCard'
import { useSalesAuth } from '@/lib/sales-auth'
import { getCanadaPortalRegion } from '@/lib/regions'
import { RegionHero } from '@/components/RegionHero'

export default function CanadaPortalTrainingPage() {
  const { rep } = useSalesAuth()
  // Region members get their territory's accent + an orientation card on top
  // of the SAME gated course — completion requirements are identical.
  const region = getCanadaPortalRegion(rep?.region)
  const accent = region?.theme.accent ?? '#17C5B0'

  return (
    <div className="space-y-6">
      {/* Odyssey hero — every Canada rep; a member's own region theme wins */}
      {region && <RegionHero region={region} videoSrc="/regions/odyssey/training-hero.mp4" focus="50% 16%" />}

      <header className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl border flex items-center justify-center"
          style={{ backgroundColor: `${accent}1a`, borderColor: `${accent}33` }}
        >
          <GraduationCap size={18} style={{ color: accent }} />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">
            {region ? `${region.name} — Training & Playbook` : 'Training & Playbook'}
          </h1>
          <p className="text-2xs text-pm-canada-text-muted">
            Complete the course to unlock lead creation, then use the playbook to find any answer in 30 seconds.
          </p>
        </div>
      </header>

      {region && <RegionOrientationCard region={region} />}

      <DemoCallCard accent={accent} variant="portal" />

      <TrainingCourse accent={accent} />

      <ComplianceGuidesCard accent={accent} />

      <PlaybookViewer country="canada" />
    </div>
  )
}
