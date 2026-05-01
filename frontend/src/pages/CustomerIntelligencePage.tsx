import { useState, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  Eye, BarChart3, Users, UserCheck, Lightbulb,
  TrendingUp, TrendingDown, ArrowRight, Camera,
} from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import FootTrafficFunnel from '@/components/vision/FootTrafficFunnel'
import ZoneHeatmap from '@/components/vision/ZoneHeatmap'
import CustomerProfileCard from '@/components/vision/CustomerProfileCard'
import VisionInsightCard from '@/components/vision/VisionInsightCard'

const API = import.meta.env.VITE_API_URL || ''

type Tab = 'overview' | 'traffic' | 'demographics' | 'profiles' | 'insights'

const tabs: { key: Tab; label: string; icon: typeof Eye }[] = [
  { key: 'overview', label: 'Live', icon: Eye },
  { key: 'traffic', label: 'Foot Traffic', icon: BarChart3 },
  { key: 'demographics', label: 'Demographics', icon: Users },
  { key: 'profiles', label: 'Profiles', icon: UserCheck },
  { key: 'insights', label: 'AI Insights', icon: Lightbulb },
]

async function fetchTraffic(orgId: string, days = 7) {
  const r = await fetch(`${API}/api/vision/foot-traffic/${orgId}?days=${days}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function fetchDemographics(orgId: string, days = 7) {
  const r = await fetch(`${API}/api/vision/demographics/${orgId}?days=${days}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function fetchHeatmap(orgId: string, days = 7) {
  const r = await fetch(`${API}/api/vision/heatmap/${orgId}?days=${days}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function fetchProfiles(orgId: string, sort = 'last_seen', limit = 50) {
  const r = await fetch(`${API}/api/vision/customers/${orgId}?sort=${sort}&limit=${limit}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function fetchProfileDetail(orgId: string, profileId: string) {
  const r = await fetch(`${API}/api/vision/customers/${orgId}/${profileId}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function fetchFunnel(orgId: string, days = 7) {
  const r = await fetch(`${API}/api/vision/conversion-funnel/${orgId}?days=${days}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function fetchInsights(orgId: string) {
  const r = await fetch(`${API}/api/vision/insights/${orgId}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

export default function CustomerIntelligencePage() {
  const [tab, setTab] = useState<Tab>('overview')
  const [days, setDays] = useState(7)
  const [profileSort, setProfileSort] = useState('last_seen')
  const [profileFilter, setProfileFilter] = useState<'all' | 'returning' | 'new' | 'vip'>('all')
  const [expandedProfile, setExpandedProfile] = useState<string | null>(null)
  const [profileVisits, setProfileVisits] = useState<Record<string, any[]>>({})

  const orgId = 'demo'

  const traffic = useApi(() => fetchTraffic(orgId, days), [days])
  const demographics = useApi(() => fetchDemographics(orgId, days), [days])
  const heatmap = useApi(() => fetchHeatmap(orgId, days), [days])
  const profiles = useApi(() => fetchProfiles(orgId, profileSort), [profileSort])
  const funnel = useApi(() => fetchFunnel(orgId, days), [days])
  const insights = useApi(() => fetchInsights(orgId), [])

  const handleExpandProfile = useCallback(async (profileId: string) => {
    if (expandedProfile === profileId) {
      setExpandedProfile(null)
      return
    }
    setExpandedProfile(profileId)
    if (!profileVisits[profileId]) {
      try {
        const detail = await fetchProfileDetail(orgId, profileId)
        setProfileVisits(prev => ({ ...prev, [profileId]: detail.visits || [] }))
      } catch {
        setProfileVisits(prev => ({ ...prev, [profileId]: [] }))
      }
    }
  }, [expandedProfile, profileVisits, orgId])

  const summary = traffic.data?.summary || {}
  const funnelData = funnel.data || {}
  const demo = demographics.data?.demographics || {}
  const heatData = heatmap.data?.heatmap || {}
  const profileList = profiles.data?.profiles || []
  const insightList = insights.data?.insights || []

  const filteredProfiles = profileList.filter((p: any) => {
    if (profileFilter === 'returning') return p.visit_count >= 2
    if (profileFilter === 'new') return p.visit_count === 1
    if (profileFilter === 'vip') return p.visit_count >= 10
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center">
          <Camera size={20} className="text-[#1A8FD6]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Customer Intelligence</h1>
          <p className="text-sm text-[#A1A1A8]">Vision-powered analytics</p>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="period-toggle overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={clsx(
              tab === t.key ? 'period-btn-active' : 'period-btn-inactive',
              'flex items-center gap-1.5 whitespace-nowrap',
            )}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab 1: Live Overview ── */}
      {tab === 'overview' && (
        <div className="space-y-4">
          {traffic.loading ? <LoadingPage /> : traffic.error ? (
            <ErrorState message={traffic.error} onRetry={traffic.refetch} />
          ) : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatBox label="Passersby" value={summary.total_passersby || 0} />
                <StatBox label="Walk-ins" value={summary.walk_ins || 0}
                  sub={`${Math.round((summary.walk_in_conversion || 0) * 100)}% conversion`}
                  subColor={summary.walk_in_conversion > 0.3 ? 'text-[#4FE3C1]' : 'text-amber-400'} />
                <StatBox label="Returning" value={summary.returning_visitors || 0}
                  sub={`${summary.new_faces || 0} new faces`} />
                <StatBox label="Non-customers" value={summary.non_customers || 0}
                  sub="browsed, didn't buy" subColor="text-amber-400" />
              </div>

              {/* Gender donut placeholder */}
              {demo.gender && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div className="card p-4">
                    <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-3 font-medium">Gender Split</p>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="h-3 rounded-full overflow-hidden flex bg-[#1F1F23]">
                          <div className="bg-[#1A8FD6] rounded-l-full" style={{ width: `${demo.gender.male_pct || 50}%` }} />
                          <div className="bg-[#7C5CFF] rounded-r-full" style={{ width: `${demo.gender.female_pct || 50}%` }} />
                        </div>
                        <div className="flex justify-between mt-1.5">
                          <span className="text-[10px] text-[#1A8FD6] font-mono">{demo.gender.male_pct}% M</span>
                          <span className="text-[10px] text-[#7C5CFF] font-mono">{demo.gender.female_pct}% F</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="card p-4">
                    <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-3 font-medium">Zone Activity</p>
                    <ZoneHeatmap
                      zoneVisits={heatData.zone_visits || {}}
                      zoneAvgDwell={heatData.zone_avg_dwell || {}}
                      totalVisits={heatData.total_visits || 0}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab 2: Foot Traffic ── */}
      {tab === 'traffic' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className="bg-[#1F1F23] border border-[#1F1F23] rounded-lg px-3 py-1.5 text-sm text-[#F5F5F7]"
            >
              <option value={1}>Today</option>
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
            </select>
          </div>

          {funnel.loading ? <LoadingPage /> : funnel.error ? (
            <ErrorState message={funnel.error} onRetry={funnel.refetch} />
          ) : (
            <>
              <div className="card p-5">
                <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-4 font-medium">
                  Conversion Funnel
                </p>
                <FootTrafficFunnel
                  funnel={funnelData.funnel || []}
                  dropOffs={funnelData.drop_offs || []}
                />
                {funnelData.conversion_rate != null && (
                  <p className="text-sm text-[#A1A1A8] mt-4 pt-3 border-t border-[#1F1F23]">
                    End-to-end conversion: <span className="text-[#4FE3C1] font-bold font-mono">{funnelData.conversion_rate}%</span>
                  </p>
                )}
              </div>

              {/* Callout cards */}
              {summary.window_shoppers > 0 && (
                <div className="card p-4 border-l-2 border-amber-400">
                  <p className="text-sm font-semibold text-[#F5F5F7]">
                    {summary.window_shoppers} people looked but didn't enter
                  </p>
                  <p className="text-xs text-[#A1A1A8] mt-1">
                    That's {Math.round(summary.window_shoppers / Math.max(summary.total_passersby, 1) * 100)}% of all passersby.
                    Improve storefront signage or window displays to convert them.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab 3: Demographics ── */}
      {tab === 'demographics' && (
        <div className="space-y-4">
          {demographics.loading ? <LoadingPage /> : demographics.error ? (
            <ErrorState message={demographics.error} onRetry={demographics.refetch} />
          ) : (
            <>
              <div className="card p-5">
                <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-3 font-medium">Gender over time</p>
                {demo.daily_gender && Object.keys(demo.daily_gender).length > 0 ? (
                  <div className="space-y-1.5">
                    {Object.entries(demo.daily_gender as Record<string, { male: number; female: number }>)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .slice(-14)
                      .map(([day, data]) => {
                        const total = data.male + data.female
                        const malePct = total > 0 ? Math.round(data.male / total * 100) : 50
                        return (
                          <div key={day} className="flex items-center gap-2">
                            <span className="text-[10px] text-[#A1A1A8]/40 font-mono w-16">{day.slice(5)}</span>
                            <div className="flex-1 h-4 rounded-full overflow-hidden flex bg-[#1F1F23]">
                              <div className="bg-[#1A8FD6]/70" style={{ width: `${malePct}%` }} />
                              <div className="bg-[#7C5CFF]/70" style={{ width: `${100 - malePct}%` }} />
                            </div>
                            <span className="text-[10px] text-[#A1A1A8]/40 font-mono w-8">{total}</span>
                          </div>
                        )
                      })}
                  </div>
                ) : (
                  <EmptyState title="No gender data" description="Connect cameras with demographics enabled" />
                )}
              </div>

              <div className="card p-5">
                <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-3 font-medium">Age Distribution</p>
                {demo.age_buckets && Object.keys(demo.age_buckets).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(demo.age_buckets as Record<string, number>)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([bucket, count]) => {
                        const totalAge = Object.values(demo.age_buckets as Record<string, number>).reduce((a, b) => a + b, 0)
                        const pct = Math.round(count / Math.max(totalAge, 1) * 100)
                        return (
                          <div key={bucket} className="flex items-center gap-2">
                            <span className="text-xs text-[#A1A1A8] w-14 font-mono">{bucket}</span>
                            <div className="flex-1 h-5 bg-[#1F1F23] rounded-lg overflow-hidden">
                              <div className="h-full bg-[#17C5B0]/60 rounded-lg" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="text-xs text-[#A1A1A8]/50 font-mono w-10 text-right">{pct}%</span>
                          </div>
                        )
                      })}
                  </div>
                ) : (
                  <EmptyState title="No age data" description="Enable demographics in camera settings" />
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Tab 4: Customer Profiles ── */}
      {tab === 'profiles' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={profileSort}
              onChange={e => setProfileSort(e.target.value)}
              className="bg-[#1F1F23] border border-[#1F1F23] rounded-lg px-3 py-1.5 text-sm text-[#F5F5F7]"
            >
              <option value="last_seen">Last seen</option>
              <option value="visit_count">Most visits</option>
              <option value="predicted_ltv">Highest LTV</option>
            </select>
            <div className="period-toggle">
              {(['all', 'returning', 'new', 'vip'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setProfileFilter(f)}
                  className={clsx(
                    profileFilter === f ? 'period-btn-active' : 'period-btn-inactive',
                    'text-xs',
                  )}
                >
                  {f === 'vip' ? 'VIP' : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
            <span className="text-xs text-[#A1A1A8]/40 ml-auto">
              {filteredProfiles.length} profiles
            </span>
          </div>

          {profiles.loading ? <LoadingPage /> : profiles.error ? (
            <ErrorState message={profiles.error} onRetry={profiles.refetch} />
          ) : filteredProfiles.length === 0 ? (
            <EmptyState title="No customer profiles" description="Profiles appear when cameras detect visitors with opt_in_identity mode" />
          ) : (
            <div className="space-y-2">
              {filteredProfiles.map((p: any) => (
                <CustomerProfileCard
                  key={p.id}
                  profile={p}
                  expanded={expandedProfile === p.id}
                  onExpand={handleExpandProfile}
                  visits={profileVisits[p.id]}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Tab 5: AI Insights ── */}
      {tab === 'insights' && (
        <div className="space-y-3">
          {insights.loading ? <LoadingPage /> : insights.error ? (
            <ErrorState message={insights.error} onRetry={insights.refetch} />
          ) : insightList.length === 0 ? (
            <EmptyState title="No insights yet" description="Insights are generated after cameras collect enough data" />
          ) : (
            insightList.map((ins: any, i: number) => (
              <VisionInsightCard key={ins.id || i} insight={ins} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

function StatBox({ label, value, sub, subColor }: {
  label: string; value: number; sub?: string; subColor?: string
}) {
  return (
    <div className="card p-4">
      <p className="text-xs text-[#A1A1A8] uppercase tracking-wider font-medium">{label}</p>
      <p className="text-2xl font-bold text-[#F5F5F7] font-mono mt-1">{value.toLocaleString()}</p>
      {sub && <p className={clsx('text-[10px] mt-0.5', subColor || 'text-[#A1A1A8]/50')}>{sub}</p>}
    </div>
  )
}
