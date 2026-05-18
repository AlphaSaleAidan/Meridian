import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MeridianEmblem } from '@/components/MeridianLogo'

export default function CustomerPortalRedirect() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) { setError('Invalid portal link'); return }

    const apiUrl = import.meta.env.VITE_API_URL || ''
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 10000)

    fetch(`${apiUrl}/api/portal/resolve/${token}`, { signal: controller.signal })
      .then(res => {
        if (res.status === 404) throw new Error('Portal link expired or invalid')
        if (res.status === 400) throw new Error('Invalid portal link format')
        if (!res.ok) throw new Error(`Server error (${res.status}). Please try again.`)
        return res.json()
      })
      .then(data => {
        localStorage.setItem('meridian_portal_token', token)
        localStorage.setItem('meridian_portal_org', JSON.stringify(data))
        navigate(`/canada/login?org=${data.org_id}`, { replace: true })
      })
      .catch(err => {
        if (err.name === 'AbortError') {
          setError('Connection timed out. Please check your internet and try again.')
        } else if (err instanceof TypeError) {
          setError('Unable to connect to Meridian. Please check your internet connection.')
        } else {
          setError(err.message)
        }
      })
      .finally(() => clearTimeout(timeout))

    return () => { controller.abort(); clearTimeout(timeout) }
  }, [token, navigate])

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0f0d] flex flex-col items-center justify-center px-4">
        <MeridianEmblem size={40} />
        <h1 className="text-xl font-bold text-white mt-4">Link Not Found</h1>
        <p className="text-[13px] text-[#6b7a74] mt-2 text-center max-w-sm">{error}</p>
        <a href="https://meridian.tips/canada" className="mt-6 text-[13px] text-[#00d4aa] hover:underline">
          Go to Meridian Canada
        </a>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0f0d] flex flex-col items-center justify-center">
      <MeridianEmblem size={40} />
      <div className="mt-4 w-5 h-5 border-2 border-[#00d4aa] border-t-transparent rounded-full animate-spin" />
      <p className="text-[12px] text-[#6b7a74] mt-3">Loading your portal...</p>
    </div>
  )
}
