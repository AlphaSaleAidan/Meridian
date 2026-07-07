import { GraduationCap } from 'lucide-react'
import PlaybookViewer from '@/components/training/PlaybookViewer'
import ComplianceGuidesCard from '@/components/training/ComplianceGuidesCard'
import TrainingCourse from '@/components/training/TrainingCourse'

export default function CanadaPortalTrainingPage() {
  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-pm-accent/10 border border-pm-accent/20 flex items-center justify-center">
          <GraduationCap size={18} className="text-pm-accent" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">Training &amp; Playbook</h1>
          <p className="text-2xs text-pm-canada-text-muted">
            Complete the course to unlock lead creation, then use the playbook to find any answer in 30 seconds.
          </p>
        </div>
      </header>

      <TrainingCourse accent="#17C5B0" />

      <ComplianceGuidesCard accent="#17C5B0" />

      <PlaybookViewer country="canada" />
    </div>
  )
}
