import { GraduationCap } from 'lucide-react'
import PlaybookViewer from '@/components/training/PlaybookViewer'

export default function CanadaPortalTrainingPage() {
  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-pm-accent/10 border border-pm-accent/20 flex items-center justify-center">
          <GraduationCap size={18} className="text-pm-accent" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">Sales Rep Playbook</h1>
          <p className="text-2xs text-pm-canada-text-muted">
            Find any answer in 30 seconds. POS integrations, camera setup, features, troubleshooting, cheat sheets.
          </p>
        </div>
      </header>

      <PlaybookViewer country="canada" />
    </div>
  )
}
