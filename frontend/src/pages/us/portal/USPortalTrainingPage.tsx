import { GraduationCap } from 'lucide-react'
import PlaybookViewer from '@/components/training/PlaybookViewer'
import ComplianceGuidesCard from '@/components/training/ComplianceGuidesCard'
import TrainingCourse from '@/components/training/TrainingCourse'

export default function USPortalTrainingPage() {
  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center">
          <GraduationCap size={18} className="text-[#00d4aa]" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">Training &amp; Playbook</h1>
          <p className="text-[11px] text-[#6b7a74]">
            Complete the course to unlock lead creation, then use the playbook to find any answer in 30 seconds.
          </p>
        </div>
      </header>

      <TrainingCourse accent="#00d4aa" />

      <ComplianceGuidesCard accent="#00d4aa" />

      <PlaybookViewer country="us" />
    </div>
  )
}
