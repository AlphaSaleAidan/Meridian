import { useParams } from 'react-router-dom'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

export default function CanadaInvoicePage() {
  const { invoiceId } = useParams<{ invoiceId: string }>()

  return (
    <div className="min-h-screen bg-[#0a0f0d] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md text-center space-y-6">
        <div className="flex items-center justify-center gap-2.5">
          <MeridianEmblem size={36} />
          <MeridianWordmark className="text-xl" />
        </div>

        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-6 space-y-4">
          <h1 className="text-lg font-bold text-white">Invoice #{invoiceId}</h1>
          <p className="text-sm text-[#6b7a74]">
            This invoice is managed by your Meridian sales representative. Contact them for payment details or to view the full invoice PDF.
          </p>

          <div className="p-3 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
            <p className="text-xs text-[#00d4aa] font-medium">Recurring Monthly — All prices in CAD</p>
          </div>

          <a
            href="/canada/login"
            className="block w-full py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all text-center"
          >
            Log In to Your Dashboard
          </a>
        </div>

        <p className="text-[10px] text-[#4a5550]">Meridian Intelligence Inc. — Canada</p>
      </div>
    </div>
  )
}
