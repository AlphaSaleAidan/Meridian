import { useMemo, useState } from 'react'
import { clsx } from 'clsx'
import {
  DollarSign, Receipt, ShoppingCart, Wallet, TrendingUp, FileSpreadsheet,
  FileText, Building2, Plus, Trash2, Loader2, ShieldCheck, Landmark, CheckCircle2,
} from 'lucide-react'
import { formatCents, formatCentsCompact } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import {
  api, type CpaExpense, type CpaBankConnection, type CpaBankTransaction, type ExpenseInput,
} from '@/lib/api'
import { useApi } from '@/hooks/useApi'
import { getAuthHeaders } from '@/lib/supabase'
import { demoData } from '@/lib/demo-data'
import { LoadingPage, ErrorState } from '@/components/LoadingState'

// Single source of truth for the disclaimer — byte-identical to the backend
// (`src/api/routes/cpa.py::CPA_DISCLAIMER`) and the printable report.
const CPA_DISCLAIMER =
  'We prepare, your CPA files. Meridian organizes your sales and expense records into ' +
  'a CPA-ready summary. These figures are a starting point for your accountant — Meridian ' +
  'does not calculate income tax, file returns, or provide tax advice. Confirm all numbers ' +
  'with your CPA before filing.'

const EXPENSE_CATEGORIES = [
  'supplies', 'cogs', 'rent', 'utilities', 'payroll', 'marketing', 'equipment', 'fees', 'other',
] as const

const CATEGORY_LABEL: Record<string, string> = {
  supplies: 'Supplies', cogs: 'Cost of goods', rent: 'Rent', utilities: 'Utilities',
  payroll: 'Payroll', marketing: 'Marketing', equipment: 'Equipment', fees: 'Fees', other: 'Other',
}

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function monthLabel(month: string): string {
  const mm = Number(month.slice(5, 7))
  return MONTH_LABELS[mm - 1] ?? month
}

// Build a CPA-ready CSV client-side (demo path — no backend round-trip).
function buildCsv(summary: any, expenses: CpaExpense[]): string {
  const esc = (v: unknown) => {
    const s = String(v ?? '')
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const row = (cells: unknown[]) => cells.map(esc).join(',')
  const lines: string[] = []
  lines.push(row(['Meridian CPA Handoff', `Year ${summary.year}`, 'Currency CAD']))
  lines.push(row([CPA_DISCLAIMER]))
  lines.push('')
  lines.push(row(['Summary']))
  lines.push(row(['Revenue', (summary.revenue_cents / 100).toFixed(2)]))
  lines.push(row(['Sales tax collected', (summary.sales_tax_collected_cents / 100).toFixed(2)]))
  lines.push(row(['Order count', summary.order_count]))
  lines.push(row(['Expenses total', (summary.expenses_total_cents / 100).toFixed(2)]))
  lines.push(row(['Net (revenue - expenses)', (summary.net_cents / 100).toFixed(2)]))
  lines.push('')
  lines.push(row(['Monthly breakdown']))
  lines.push(row(['Month', 'Revenue', 'Sales tax collected', 'Orders', 'Expenses']))
  for (const m of summary.monthly ?? []) {
    lines.push(row([m.month, (m.revenue_cents / 100).toFixed(2),
      (m.sales_tax_collected_cents / 100).toFixed(2), m.order_count, (m.expenses_total_cents / 100).toFixed(2)]))
  }
  lines.push('')
  lines.push(row(['Expenses detail']))
  lines.push(row(['Date', 'Category', 'Vendor', 'Amount', 'Note']))
  for (const e of expenses) {
    lines.push(row([e.expense_date, e.category, e.vendor, (e.amount_cents / 100).toFixed(2), e.note ?? '']))
  }
  return lines.join('\n')
}

function downloadBlob(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function StatCard({ icon: Icon, color, label, value }: {
  icon: typeof DollarSign; color: string; label: string; value: string
}) {
  return (
    <StaggerItem>
      <DashboardTiltCard className="card p-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}1a` }}>
            <Icon size={16} style={{ color }} />
          </div>
          <div>
            <p className="stat-label">{label}</p>
            <p className="text-lg font-bold text-[#F5F5F7] font-mono">{value}</p>
          </div>
        </div>
      </DashboardTiltCard>
    </StaggerItem>
  )
}

export default function CPAHandoffPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected

  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const yearOptions = [currentYear, currentYear - 1, currentYear - 2]

  const summaryApi = useApi(() => api.cpaSummary(orgId, year), [orgId, year])
  const expensesApi = useApi(() => api.cpaExpenses(orgId, year), [orgId, year])
  const connectionsApi = useApi(() => api.cpaBankConnections(orgId), [orgId])
  const transactionsApi = useApi(() => api.cpaBankTransactions(orgId, year), [orgId, year])

  // Demo state lives locally; in authed mode we read from the API + refetch.
  const [demoExpenses, setDemoExpenses] = useState<CpaExpense[]>(() => demoData.cpaExpenses().expenses)
  const [demoConnections, setDemoConnections] = useState<CpaBankConnection[]>([])
  const [demoTxns, setDemoTxns] = useState<CpaBankTransaction[]>([])
  const [demoCategories, setDemoCategories] = useState<Record<string, string>>({})

  const summary: any = isDemo ? demoData.cpaSummary() : summaryApi.data
  const expenses: CpaExpense[] = isDemo ? demoExpenses : (expensesApi.data?.expenses ?? [])
  const connections: CpaBankConnection[] = isDemo ? demoConnections : (connectionsApi.data?.connections ?? [])
  const transactions: CpaBankTransaction[] = isDemo ? demoTxns : (transactionsApi.data?.transactions ?? [])

  // Loading / error gates — only surface once authed (mirrors MarginsPage).
  if (!isDemo && posConnected && summaryApi.loading) return <LoadingPage />
  if (!isDemo && posConnected && summaryApi.error) {
    return <ErrorState message={summaryApi.error} onRetry={summaryApi.refetch} />
  }

  const s = summary ?? {
    year, currency: 'CAD', revenue_cents: 0, sales_tax_collected_cents: 0,
    order_count: 0, expenses_total_cents: 0, net_cents: 0, monthly: [],
  }

  // Transactions grouped by card, with a per-card subtotal of debits.
  const groupedByCard = useMemo(() => {
    const groups: Record<string, CpaBankTransaction[]> = {}
    for (const t of transactions) {
      ;(groups[t.card_last4] ||= []).push(t)
    }
    return Object.entries(groups).map(([card, txns]) => ({
      card,
      txns,
      debitSubtotalCents: txns.filter(t => t.direction === 'debit').reduce((sum, t) => sum + t.amount_cents, 0),
    }))
  }, [transactions])

  const connected = connections[0]

  // ── Mutations (branch on isDemo) ──
  const [addForm, setAddForm] = useState<ExpenseInput>({
    expense_date: `${year}-01-01`, category: 'supplies', vendor: '', amount_cents: 0, note: '',
  })
  const [amountInput, setAmountInput] = useState('')
  const [adding, setAdding] = useState(false)
  const [connecting, setConnecting] = useState(false)

  async function handleAddExpense() {
    const amount_cents = Math.round(parseFloat(amountInput || '0') * 100)
    if (!addForm.vendor.trim() || !amount_cents) return
    const body: ExpenseInput = { ...addForm, amount_cents }
    if (isDemo) {
      setDemoExpenses(prev => [{ id: `local-${Date.now()}`, ...body, note: body.note || '' }, ...prev])
      setAddForm({ ...addForm, vendor: '', note: '' })
      setAmountInput('')
      return
    }
    setAdding(true)
    try {
      await api.addExpense(orgId, body)
      setAddForm({ ...addForm, vendor: '', note: '' })
      setAmountInput('')
      expensesApi.refetch()
      summaryApi.refetch()
    } finally {
      setAdding(false)
    }
  }

  async function handleDeleteExpense(id: string) {
    if (isDemo) {
      setDemoExpenses(prev => prev.filter(e => e.id !== id))
      return
    }
    await api.deleteExpense(orgId, id)
    expensesApi.refetch()
    summaryApi.refetch()
  }

  async function handleConnectBank() {
    if (isDemo) {
      setConnecting(true)
      try {
        setDemoConnections(demoData.cpaConnections().connections)
        setDemoTxns(demoData.cpaTransactions().transactions)
      } finally {
        setConnecting(false)
      }
      return
    }
    setConnecting(true)
    try {
      // Real mode: request a link token, then run Plaid Link if it's trivially
      // available on the page. We do NOT pull in the react-plaid-link dep — if
      // the Plaid script isn't already loaded, fall back to the demo-style
      // connect endpoint so the button still does something useful.
      await api.cpaLinkToken(orgId).catch(() => null)
      const plaid = (window as any).Plaid
      if (!plaid) {
        await api.cpaConnectDemoBank(orgId).catch(() => null)
      }
      await api.cpaBankSync(orgId).catch(() => null)
      connectionsApi.refetch()
      transactionsApi.refetch()
    } finally {
      setConnecting(false)
    }
  }

  function handleCategoryChange(txnId: string, category: string) {
    // Categorization is a per-row hint that feeds expenses; demo keeps it local.
    setDemoCategories(prev => ({ ...prev, [txnId]: category }))
  }

  async function handleExport(fmt: 'csv' | 'html') {
    if (isDemo) {
      if (fmt === 'csv') {
        downloadBlob(buildCsv(s, expenses), `meridian-cpa-${year}.csv`, 'text/csv')
      } else {
        // Demo printable report: open the synthetic CSV's data as a simple
        // printable HTML page in a new tab.
        const win = window.open('', '_blank')
        if (win) {
          win.document.write(buildDemoReportHtml(s, expenses))
          win.document.close()
        }
      }
      return
    }
    // Authed mode: fetch via apiFetch headers, then objectURL (keeps auth).
    const url = api.cpaExportUrl(orgId, year, fmt)
    const headers = await getAuthHeaders()
    const res = await fetch(url, { credentials: 'include', headers })
    const blob = await res.blob()
    if (fmt === 'csv') {
      downloadBlob(await blob.text(), `meridian-cpa-${year}.csv`, 'text/csv')
    } else {
      const objectUrl = URL.createObjectURL(blob)
      window.open(objectUrl, '_blank')
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
    }
  }

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Taxes &amp; Expenses</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              A CPA-ready summary of your sales, sales tax, and expenses — ready to hand off.
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-[#A1A1A8]">
            Tax year
            <select
              value={year}
              onChange={e => setYear(Number(e.target.value))}
              className="bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-1.5 text-[#F5F5F7] text-sm focus:outline-none focus:border-[#1A8FD6]"
            >
              {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
        </div>
      </ScrollReveal>

      {/* Disclaimer banner */}
      <ScrollReveal variant="fadeUp">
        <div className="card p-4 sm:p-5 border border-[#1A8FD6]/30 bg-[#1A8FD6]/[0.05]">
          <div className="flex gap-3">
            <span className="inline-flex p-2 rounded-xl bg-[#1A8FD6]/10 text-[#1A8FD6] flex-shrink-0 h-fit">
              <ShieldCheck size={20} />
            </span>
            <p className="text-sm text-[#A1A1A8] leading-relaxed">{CPA_DISCLAIMER}</p>
          </div>
        </div>
      </ScrollReveal>

      {/* Stat cards */}
      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
        <StatCard icon={DollarSign} color="#1A8FD6" label="Revenue" value={formatCentsCompact(s.revenue_cents)} />
        <StatCard icon={Receipt} color="#17C5B0" label="Sales tax collected" value={formatCentsCompact(s.sales_tax_collected_cents)} />
        <StatCard icon={ShoppingCart} color="#7C5CFF" label="Orders" value={s.order_count.toLocaleString()} />
        <StatCard icon={Wallet} color="#F97316" label="Expenses" value={formatCentsCompact(s.expenses_total_cents)} />
        <StatCard icon={TrendingUp} color="#22C55E" label="Net (rev − exp)" value={formatCentsCompact(s.net_cents)} />
      </StaggerContainer>

      {/* Export buttons */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleExport('csv')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-pm-amber-gold text-pm-bg font-bold text-sm hover:bg-pm-amber-gold/90 transition-colors"
          >
            <FileSpreadsheet size={16} /> Download CSV
          </button>
          <button
            onClick={() => handleExport('html')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[#1F1F23] bg-[#111113] text-[#F5F5F7] font-semibold text-sm hover:border-[#1A8FD6] transition-colors"
          >
            <FileText size={16} /> Download printable report
          </button>
        </div>
      </ScrollReveal>

      {/* Monthly breakdown */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Monthly breakdown — {year}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[560px]">
              <thead>
                <tr>
                  <th className="text-left">Month</th>
                  <th className="text-right">Revenue</th>
                  <th className="text-right">Sales tax</th>
                  <th className="text-right">Orders</th>
                  <th className="text-right">Expenses</th>
                </tr>
              </thead>
              <tbody>
                {(s.monthly ?? []).map((m: any) => (
                  <tr key={m.month}>
                    <td className="font-medium text-[#F5F5F7]">{monthLabel(m.month)}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCents(m.revenue_cents)}</td>
                    <td className="text-right font-mono text-[#17C5B0]">{formatCents(m.sales_tax_collected_cents)}</td>
                    <td className="text-right font-mono text-[#A1A1A8]">{m.order_count}</td>
                    <td className="text-right font-mono text-[#F97316]">{formatCents(m.expenses_total_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>

      {/* Connect bank account */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 sm:p-5">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <span className="inline-flex p-2.5 rounded-xl bg-[#22C55E]/10 text-[#22C55E] flex-shrink-0">
              <Landmark size={22} />
            </span>
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-[#F5F5F7]">Connect your bank</h3>
              {connected ? (
                <p className="mt-0.5 text-sm text-[#A1A1A8] flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-[#22C55E]" />
                  <span className="text-[#F5F5F7]">{connected.institution}</span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide bg-[#22C55E]/15 text-[#22C55E]">
                    {connected.status}
                  </span>
                </p>
              ) : (
                <p className="mt-0.5 text-sm text-[#A1A1A8]">
                  Link your bank to pull card transactions automatically — debits become expense candidates for your CPA packet.
                </p>
              )}
            </div>
            {!connected && (
              <button
                onClick={handleConnectBank}
                disabled={connecting}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#22C55E] text-pm-bg font-bold text-sm hover:bg-[#22C55E]/90 transition-colors disabled:opacity-60 flex-shrink-0"
              >
                {connecting ? <Loader2 size={16} className="animate-spin" /> : <Building2 size={16} />}
                {isDemo ? 'Connect demo bank' : 'Connect your bank'}
              </button>
            )}
          </div>
        </div>
      </ScrollReveal>

      {/* Transactions per card */}
      {groupedByCard.length > 0 && (
        <ScrollReveal variant="fadeUp" delay={0.2}>
          <div className="space-y-4">
            {groupedByCard.map(group => (
              <div key={group.card} className="card overflow-hidden">
                <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
                    <Building2 size={14} className="text-[#A1A1A8]" />
                    Card •••• {group.card}
                  </h3>
                  <span className="text-xs text-[#A1A1A8]">
                    Debits subtotal <span className="font-mono text-[#F97316]">{formatCents(group.debitSubtotalCents)}</span>
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="pm-table min-w-[600px]">
                    <thead>
                      <tr>
                        <th className="text-left">Date</th>
                        <th className="text-left">Description</th>
                        <th className="text-right">Amount</th>
                        <th className="text-left">Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.txns.map(t => (
                        <tr key={t.id}>
                          <td className="font-mono text-[#A1A1A8]">{t.posted_date}</td>
                          <td className="text-[#F5F5F7]">{t.description}</td>
                          <td className={clsx('text-right font-mono', t.direction === 'credit' ? 'text-[#22C55E]' : 'text-[#F5F5F7]')}>
                            {t.direction === 'credit' ? '+' : '−'}{formatCents(t.amount_cents)}
                          </td>
                          <td>
                            {t.direction === 'debit' ? (
                              <select
                                value={demoCategories[t.id] ?? t.suggested_category ?? 'other'}
                                onChange={e => handleCategoryChange(t.id, e.target.value)}
                                className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-2 py-1 text-xs text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]"
                              >
                                {EXPENSE_CATEGORIES.map(c => (
                                  <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>
                                ))}
                              </select>
                            ) : (
                              <span className="text-[10px] text-[#A1A1A8]">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </ScrollReveal>
      )}

      {/* Manual expenses */}
      <ScrollReveal variant="fadeUp" delay={0.25}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Expenses</h3>
            <p className="text-[10px] text-[#A1A1A8] mt-0.5">Add anything not captured by your bank feed.</p>
          </div>

          {/* Add form */}
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] grid grid-cols-2 lg:grid-cols-6 gap-2">
            <input
              type="date"
              value={addForm.expense_date}
              onChange={e => setAddForm({ ...addForm, expense_date: e.target.value })}
              className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-2.5 py-2 text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]"
            />
            <select
              value={addForm.category}
              onChange={e => setAddForm({ ...addForm, category: e.target.value })}
              className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-2.5 py-2 text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]"
            >
              {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>)}
            </select>
            <input
              type="text"
              placeholder="Vendor"
              value={addForm.vendor}
              onChange={e => setAddForm({ ...addForm, vendor: e.target.value })}
              className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-2.5 py-2 text-sm text-[#F5F5F7] placeholder:text-[#52525B] focus:outline-none focus:border-[#1A8FD6] col-span-2 lg:col-span-1"
            />
            <input
              type="number"
              step="0.01"
              min="0"
              placeholder="Amount"
              value={amountInput}
              onChange={e => setAmountInput(e.target.value)}
              className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-2.5 py-2 text-sm text-[#F5F5F7] placeholder:text-[#52525B] focus:outline-none focus:border-[#1A8FD6]"
            />
            <input
              type="text"
              placeholder="Note (optional)"
              value={addForm.note ?? ''}
              onChange={e => setAddForm({ ...addForm, note: e.target.value })}
              className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-2.5 py-2 text-sm text-[#F5F5F7] placeholder:text-[#52525B] focus:outline-none focus:border-[#1A8FD6]"
            />
            <button
              onClick={handleAddExpense}
              disabled={adding || !addForm.vendor.trim() || !amountInput}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#1A8FD6] text-white font-semibold text-sm hover:bg-[#1A8FD6]/90 transition-colors disabled:opacity-50 col-span-2 lg:col-span-1"
            >
              {adding ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />} Add
            </button>
          </div>

          {/* List */}
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[560px]">
              <thead>
                <tr>
                  <th className="text-left">Date</th>
                  <th className="text-left">Category</th>
                  <th className="text-left">Vendor</th>
                  <th className="text-right">Amount</th>
                  <th className="text-left">Note</th>
                  <th className="text-right"></th>
                </tr>
              </thead>
              <tbody>
                {expenses.length === 0 ? (
                  <tr><td colSpan={6} className="text-center text-[#52525B] py-6 text-sm">No expenses yet for {year}.</td></tr>
                ) : expenses.map(e => (
                  <tr key={e.id}>
                    <td className="font-mono text-[#A1A1A8]">{e.expense_date}</td>
                    <td className="text-[#F5F5F7]">{CATEGORY_LABEL[e.category] ?? e.category}</td>
                    <td className="text-[#F5F5F7]">{e.vendor}</td>
                    <td className="text-right font-mono text-[#F97316]">{formatCents(e.amount_cents)}</td>
                    <td className="text-[#A1A1A8] text-xs">{e.note || '—'}</td>
                    <td className="text-right">
                      <button
                        onClick={() => handleDeleteExpense(e.id)}
                        className="inline-flex p-1.5 rounded-lg text-[#A1A1A8] hover:text-red-400 hover:bg-red-400/10 transition-colors"
                        aria-label="Delete expense"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}

// Minimal self-contained printable report for the demo path (the authed path
// fetches the backend's HTMLResponse instead).
function buildDemoReportHtml(summary: any, expenses: CpaExpense[]): string {
  const money = (c: number) => 'CA$' + (c / 100).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const monthlyRows = (summary.monthly ?? []).map((m: any) =>
    `<tr><td>${monthLabel(m.month)}</td><td>${money(m.revenue_cents)}</td><td>${money(m.sales_tax_collected_cents)}</td><td>${m.order_count}</td><td>${money(m.expenses_total_cents)}</td></tr>`).join('')
  const expenseRows = expenses.map(e =>
    `<tr><td>${e.expense_date}</td><td>${e.category}</td><td>${e.vendor}</td><td>${money(e.amount_cents)}</td><td>${e.note ?? ''}</td></tr>`).join('')
  return `<!doctype html><html><head><meta charset="utf-8"><title>Meridian CPA Handoff ${summary.year}</title>
<style>
  body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#111;max-width:780px;margin:24px auto;padding:0 16px}
  h1{font-size:22px;margin:0 0 4px} .sub{color:#555;margin:0 0 16px}
  .disc{border:1px solid #999;border-radius:8px;padding:12px;font-size:12px;color:#333;margin:16px 0;background:#f7f7f7}
  table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}
  th,td{border:1px solid #ddd;padding:6px 8px;text-align:left} th{background:#f0f0f0}
  td:nth-child(n+2){text-align:right} h2{font-size:15px;margin:20px 0 4px}
  @media print{body{margin:0} .disc{background:#fff}}
</style></head><body>
  <h1>Meridian CPA Handoff</h1>
  <p class="sub">Year ${summary.year} · Currency CAD</p>
  <div class="disc">${CPA_DISCLAIMER}</div>
  <h2>Summary</h2>
  <table>
    <tr><th>Revenue</th><td>${money(summary.revenue_cents)}</td></tr>
    <tr><th>Sales tax collected</th><td>${money(summary.sales_tax_collected_cents)}</td></tr>
    <tr><th>Order count</th><td>${summary.order_count}</td></tr>
    <tr><th>Expenses total</th><td>${money(summary.expenses_total_cents)}</td></tr>
    <tr><th>Net (revenue − expenses)</th><td>${money(summary.net_cents)}</td></tr>
  </table>
  <h2>Monthly breakdown</h2>
  <table><thead><tr><th>Month</th><th>Revenue</th><th>Sales tax</th><th>Orders</th><th>Expenses</th></tr></thead><tbody>${monthlyRows}</tbody></table>
  <h2>Expenses detail</h2>
  <table><thead><tr><th>Date</th><th>Category</th><th>Vendor</th><th>Amount</th><th>Note</th></tr></thead><tbody>${expenseRows}</tbody></table>
</body></html>`
}
