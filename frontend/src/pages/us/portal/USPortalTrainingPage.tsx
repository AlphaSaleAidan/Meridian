import { GraduationCap } from 'lucide-react'
import PlaybookViewer from '@/components/training/PlaybookViewer'

export default function USPortalTrainingPage() {
  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center">
          <GraduationCap size={18} className="text-[#00d4aa]" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">Sales Rep Playbook</h1>
          <p className="text-[11px] text-[#6b7a74]">
            Find any answer in 30 seconds. POS integrations, camera setup, features, troubleshooting, cheat sheets.
          </p>
        </div>
      </header>

      <PlaybookViewer country="us" />
    </div>
  )
}
