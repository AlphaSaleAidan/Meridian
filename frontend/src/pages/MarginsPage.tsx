import { useState, useRef, type ChangeEvent } from 'react'
import { clsx } from 'clsx'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import {
  DollarSign, TrendingDown, AlertTriangle, Target, ChevronDown, ChevronUp, Calculator,
  UploadCloud, Loader2, CheckCircle2,
} from 'lucide-react'
import { generateMarginWaterfall, type MarginItem } from '@/lib/agent-data'
import { formatCents, formatCentsCompact } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { api } from '@/lib/api'
import { useApi } from '@/hooks/useApi'
import { supabase } from '@/lib/supabase'
import { LoadingPage, ErrorState } from '@/components/LoadingState'
import AwaitingDataBanner from '@/components/AwaitingDataBanner'

// Upload a cost sheet / restock invoice → AI extraction (inventory-docs) →
// products.cost_cents → margins compute. Reuses the inventory-docs pipeline.
function CostSheetUploader({ orgId, onComplete }: { orgId: string; onComplete: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<'idle' | 'uploading' | 'processing' | 'done' | 'error'>('idle')
  const [msg, setMsg] = useState('')

  async function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!supabase) { setState('error'); setMsg('Storage not configured.'); return }
    setState('uploading'); setMsg(file.name)
    try {
      const ext = file.name.split('.').pop() || 'bin'
      const path = `${orgId}/cost_sheet_${Date.now()}.${ext}`
      const up = await supabase.storage.from('inventory-docs').upload(path, file)
      if (up.error) throw up.error
      const ins = await supabase
        .from('inventory_document_uploads')
        .insert({ org_id: orgId, file_name: file.name, file_path: path, file_type: file.type, status: 'pending' })
        .select('id')
        .single()
      if (ins.error) throw ins.error
      const docId = (ins.data as { id: string }).id

      setState('processing'); setMsg('Reading your document…')
      await api.processInventoryDoc(orgId, docId)

      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const st = await api.inventoryDocStatus(orgId, docId)
        if (st.status === 'completed') {
          const m = st.extracted_data?._match_summary
          setState('done')
          setMsg(m
            ? `Matched ${m.matched} product${m.matched === 1 ? '' : 's'}${m.inserted ? `, added ${m.inserted} new` : ''}.`
            : 'Costs imported.')
          onComplete()
          return
        }
        if (st.status === 'failed') {
          setState('error'); setMsg(st.error_message || 'Could not read that file.'); return
        }
      }
      setState('error'); setMsg('Still processing — check back shortly.')
    } catch (err: any) {
      setState('error'); setMsg(err?.message?.slice(0, 140) || 'Upload failed.')
    }
  }

  const busy = state === 'uploading' || state === 'processing'
  return (
    <div className="flex flex-col items-start gap-1.5 flex-shrink-0">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.heic"
        onChange={handleFile}
        className="sr-only"
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-pm-amber-gold text-pm-bg font-bold text-sm hover:bg-pm-amber-gold/90 transition-colors disabled:opacity-60"
      >
        {state === 'done' ? <CheckCircle2 size={16} /> : busy ? <Loader2 size={16} className="animate-spin" /> : <UploadCloud size={16} />}
        {state === 'uploading' ? 'Uploading…' : state === 'processing' ? 'Reading…' : state === 'done' ? 'Imported' : 'Upload cost sheet'}
      </button>
      {msg && (
        <p className={clsx('text-2xs font-mono max-w-[220px]', state === 'error' ? 'text-red-400' : 'text-pm-muted')}>{msg}</p>
      )}
    </div>
  )
}

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

function FormulaBreakdown({ item }: { item: MarginItem }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-[10px] text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
        <Calculator size={10} />
        {open ? 'Hide' : 'View'} Cost Formulas
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>
      {open && (
        <div className="mt-2 p-3 bg-[#0A0A0B] rounded-lg border border-[#1F1F23] space-y-1.5">
          {item.ingredients.map(ing => (
            <div key={ing.name} className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">{ing.name}</span>
              <span className="font-mono text-[#F5F5F7]">
                {formatCents(Math.round(ing.batchCostCents / ing.batchServings))}/serving
              </span>
            </div>
          ))}
          <div className="border-t border-[#1F1F23] pt-1.5 space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Raw Cost/Serving</span>
              <span className="font-mono text-[#F5F5F7]">{formatCents(item.rawCostPerServingCents)}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Waste Factor</span>
              <span className="font-mono text-[#F5F5F7]">{(item.wasteFactor * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Waste-Adj Cost</span>
              <span className="font-mono text-[#F5F5F7]">{formatCents(item.wasteAdjustedCostCents)}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Pour Cost %</span>
              <span className="font-mono text-[#F5F5F7]">{item.pourCostPct}%</span>
            </div>
            <div className="flex justify-between text-[10px] font-semibold">
              <span className="text-[#17C5B0]">Margin/Unit</span>
              <span className="font-mono text-[#17C5B0]">{formatCents(item.marginPerUnitCents)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function MarginsPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected
  const apiData = useApi(() => api.margins(orgId), [orgId])

  const items: MarginItem[] = isDemo ? generateMarginWaterfall() : (apiData.data?.items ?? [])
  const summary = apiData.data?.summary
  const catalogTotal = summary?.catalog_total ?? 0
  const missingCost = summary?.catalog_missing_cost ?? 0
  // Prices come from the POS but cost-of-goods doesn't — prompt the merchant to
  // upload a cost sheet / restock invoice so margins stop reading as ~100%.
  const showCostPrompt = !isDemo && posConnected && catalogTotal > 0 && missingCost > 0

  // Only surface loading / error once a POS is actually connected. Before that
  // the analytics endpoint 401s — instead of a scaffold we render the real
  // (empty) margin chart shell so the merchant sees exactly what fills in.
  if (!isDemo && posConnected && apiData.loading) return <LoadingPage />
  if (!isDemo && posConnected && apiData.error) return <ErrorState message={apiData.error} onRetry={apiData.refetch} />
  const awaitingData = !isDemo && items.length === 0

  const totalRevenue = items.reduce((s, i) => s + i.revenueCents, 0)
  const totalCost = items.reduce((s, i) => s + i.costCents, 0)
  const totalMargin = items.reduce((s, i) => s + i.marginCents, 0)
  const totalLeakage = items.reduce((s, i) => s + i.leakageCents, 0)
  const avgMarginPct = totalRevenue ? Math.round(totalMargin / totalRevenue * 100) : 0

  const chartData = items.map(i => ({
    name: i.name.length > 12 ? i.name.slice(0, 10) + '..' : i.name,
    margin: i.marginPct,
    revenue: i.revenueCents / 100,
    cost: i.costCents / 100,
    leakage: i.leakageCents / 100,
  }))


  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Margin Analysis</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Margin Optimizer agent • Formula-driven cost accounting with waste-adjusted margins
          </p>
        </div>
      </ScrollReveal>

      {awaitingData && <AwaitingDataBanner posConnected={posConnected} label="margin analysis" />}

      {showCostPrompt && (
        <ScrollReveal variant="fadeUp">
          <div className="card p-4 sm:p-5 border border-pm-amber-gold/30 bg-pm-amber-gold/[0.05]">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <span className="inline-flex p-2.5 rounded-xl bg-pm-amber-gold/10 text-pm-amber-gold flex-shrink-0">
                <Calculator size={22} />
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-[#F5F5F7]">Unlock your true margins</h3>
                <p className="mt-0.5 text-sm text-[#A1A1A8]">
                  Your POS gives us the <span className="text-[#F5F5F7]">selling price</span> of every item, but not what
                  you <span className="text-[#F5F5F7]">paid</span> for it — so {missingCost} of {catalogTotal} product{catalogTotal === 1 ? '' : 's'}{' '}
                  show ~100% margin. Upload your <span className="text-[#F5F5F7]">last inventory statement or restock invoice</span>{' '}
                  (PDF, Excel, CSV, or a photo) and we'll read the costs in automatically.
                </p>
              </div>
              <CostSheetUploader orgId={orgId} onComplete={apiData.refetch} />
            </div>
          </div>
        </ScrollReveal>
      )}

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" data-walkthrough="margin-stats">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <DollarSign size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Revenue</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatCentsCompact(totalRevenue)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Target size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Avg Margin</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{avgMarginPct}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <TrendingDown size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Leakage</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatCentsCompact(totalLeakage)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <DollarSign size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Net Margin</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatCentsCompact(totalMargin - totalLeakage)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* Margin Formulas Reference */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <DashboardTiltCard className="card p-4 sm:p-5" data-walkthrough="margin-calculator">
          <div className="flex items-center gap-2 mb-3">
            <Calculator size={16} className="text-[#7C5CFF]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Active Margin Formulas</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
            {[
              ['Raw Cost/Serving', 'Batch Cost ÷ Servings per Batch'],
              ['Pour Cost %', 'COGS ÷ Revenue × 100'],
              ['Waste Factor', 'Σ(Waste% × Ingredient Cost) ÷ Total Cost'],
              ['Waste-Adj Cost', 'Raw Cost ÷ (1 − Waste Factor)'],
              ['Margin/Unit', 'Selling Price − Waste-Adj Cost'],
              ['Leakage', 'Waste Delta + Discounts + Comps'],
            ].map(([label, formula]) => (
              <div key={label} className="flex items-baseline gap-2 py-1">
                <span className="text-[10px] font-semibold text-[#F5F5F7] whitespace-nowrap">{label}</span>
                <span className="text-[10px] text-[#A1A1A8] font-mono">{formula}</span>
              </div>
            ))}
          </div>
        </DashboardTiltCard>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Margin by Product</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#F5F5F7', fontSize: 10, fontFamily: 'Geist Mono, monospace' }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}%`} domain={[0, 100]} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#F5F5F7', fontSize: 10, fontFamily: 'Geist Mono, monospace' }} axisLine={false} tickLine={false} width={90} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number) => [`${v}%`, 'Margin']}
                cursor={{ fill: 'rgba(26, 143, 214, 0.04)' }} />
              <Bar dataKey="margin" radius={[0, 4, 4, 0]} fillOpacity={0.85}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.margin >= 70 ? '#17C5B0' : entry.margin >= 60 ? '#1A8FD6' : '#F97316'} />
                ))}
                <LabelList
                  dataKey="margin"
                  position="right"
                  formatter={(v: number) => `${v}%`}
                  style={{ fill: '#F5F5F7', fontSize: 10, fontFamily: 'Geist Mono, monospace', fontWeight: 600 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ScrollReveal>

      {/* Product Cost Breakdown */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card overflow-hidden" data-walkthrough="margin-breakdown">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Product Cost Breakdown</h3>
            {summary?.has_estimates ? (
              <p className="text-[10px] text-pm-amber-gold mt-0.5">
                Rows marked <span className="font-semibold">est</span> use a typical ~{summary.est_cogs_pct}% cost-of-goods estimate for your business type — add real costs to make them exact.
              </p>
            ) : (
              <p className="text-[10px] text-[#A1A1A8] mt-0.5">Click "View Cost Formulas" on any product to see ingredient-level calculations</p>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[700px]">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Cost/Serving</th>
                  <th className="text-right">Pour Cost</th>
                  <th className="text-right">Margin</th>
                  <th className="text-right">Leakage</th>
                  <th className="text-right">Monthly Rev</th>
                </tr>
              </thead>
              <tbody>
                {items.sort((a, b) => b.revenueCents - a.revenueCents).map(item => (
                  <tr key={item.name}>
                    <td>
                      <span className="font-medium text-[#F5F5F7]">{item.name}</span>
                      {item.isEstimated && (
                        <span className="ml-2 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide bg-pm-amber-gold/15 text-pm-amber-gold align-middle">est</span>
                      )}
                      <FormulaBreakdown item={item} />
                    </td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCents(item.sellingPriceCents)}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCents(item.wasteAdjustedCostCents)}</td>
                    <td className="text-right">
                      <span className={clsx('font-mono font-medium', item.pourCostPct <= 25 ? 'text-[#17C5B0]' : item.pourCostPct <= 35 ? 'text-[#F5F5F7]' : 'text-amber-400')}>
                        {item.pourCostPct}%
                      </span>
                    </td>
                    <td className="text-right">
                      <span className={clsx('font-mono font-semibold', item.marginPct >= 70 ? 'text-[#17C5B0]' : item.marginPct >= 60 ? 'text-[#F5F5F7]' : 'text-amber-400')}>
                        {item.marginPct}%
                      </span>
                    </td>
                    <td className="text-right font-mono text-red-400">
                      {item.leakageCents > 0 ? formatCents(item.leakageCents) : '—'}
                    </td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCentsCompact(item.revenueCents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>

      {/* Leakage Details */}
      <ScrollReveal variant="fadeUp" delay={0.25}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} className="text-amber-400" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Leakage Sources</h3>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[500px]">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th className="text-right">Waste %</th>
                  <th className="text-right">Waste Cost</th>
                  <th className="text-right">Other Leakage</th>
                  <th className="text-right">Total Leakage</th>
                </tr>
              </thead>
              <tbody>
                {items.filter(i => i.leakageCents > 0).sort((a, b) => b.leakageCents - a.leakageCents).map(item => {
                  const wasteDelta = (item.wasteAdjustedCostCents - item.rawCostPerServingCents) * item.monthlySales
                  const otherLeakage = item.leakageCents - wasteDelta
                  return (
                    <tr key={item.name}>
                      <td className="font-medium text-[#F5F5F7]">{item.name}</td>
                      <td className="text-right font-mono text-[#F5F5F7]">{(item.wasteFactor * 100).toFixed(1)}%</td>
                      <td className="text-right font-mono text-amber-400">{formatCents(wasteDelta)}</td>
                      <td className="text-right font-mono text-red-400">{otherLeakage > 0 ? formatCents(otherLeakage) : '—'}</td>
                      <td className="text-right font-mono font-semibold text-red-400">{formatCents(item.leakageCents)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
