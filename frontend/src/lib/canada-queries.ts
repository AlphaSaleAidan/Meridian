/**
 * React Query hooks for the Canada sales portal.
 *
 * Centralizes the query-key scheme and mutation invalidation so every page
 * shares one cache and create/update/delete actions automatically refresh
 * sibling views (kills the audit's "no cache + manual setDeals + double
 * list() refetch" cluster of findings).
 *
 * Query-key scheme:
 *   ['canada','leads', repId | '__all__']      — list of deals scoped to a rep
 *   ['canada','lead', id]                       — single deal by id
 *
 * Mutations invalidate ['canada','leads'] (every variant) and any per-id key
 * they touch. The existing realtime subscription in `canada-leads-service`
 * is bridged into the same cache via `useCanadaLeadsRealtime` so out-of-band
 * changes (other tabs, other reps) refresh the local UI.
 */

import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { canadaLeadsService } from './canada-leads-service'
import type { Deal, DealStage } from './canada-sales-demo-data'

// ── Provider ────────────────────────────────────────────────────────────────
//
// One client for the whole /canada/* subtree. Defaults match the audit
// recommendation: ~30s staleTime, one retry, refetch on focus is OK (free
// freshness on tab switch back), but no refetch on every mount.

export function createCanadaQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        retry: 1,
        refetchOnWindowFocus: true,
        refetchOnMount: false,
      },
      mutations: {
        retry: 0,
      },
    },
  })
}

// ── Query keys ─────────────────────────────────────────────────────────────
// Plural 'leads' = list keys; singular 'lead' = detail key. They do NOT share
// a prefix on purpose, so a list invalidation will NOT touch a detail entry
// and vice versa. Every mutation that affects a single lead MUST invalidate
// both `leadsRoot()` and `lead(id)` explicitly — a leads/lead typo here will
// silently miss the cache and the UI will go stale without an error.
export const canadaKeys = {
  all: ['canada'] as const,
  leadsRoot: () => [...canadaKeys.all, 'leads'] as const,
  leads: (repId?: string) => [...canadaKeys.leadsRoot(), repId || '__all__'] as const,
  lead: (id: string) => [...canadaKeys.all, 'lead', id] as const,
}

// ── Leads list ─────────────────────────────────────────────────────────────
export function useCanadaLeads(repId: string | undefined) {
  return useQuery({
    queryKey: canadaKeys.leads(repId),
    queryFn: () => canadaLeadsService.list(repId),
    // Seed from the service's module-level cache so first paint is instant.
    initialData: () => canadaLeadsService.cached(repId) ?? undefined,
  })
}

// ── Single lead ────────────────────────────────────────────────────────────
export function useCanadaLead(id: string | undefined) {
  return useQuery({
    queryKey: id ? canadaKeys.lead(id) : ['canada', 'lead', '__none__'],
    queryFn: () => {
      if (!id) return null
      return canadaLeadsService.getById(id)
    },
    enabled: !!id,
  })
}

// ── Mutations ──────────────────────────────────────────────────────────────
export function useCreateCanadaLead(repId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (deal: Deal) => canadaLeadsService.create(deal, repId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: canadaKeys.leadsRoot() })
    },
  })
}

export function useUpdateCanadaLeadStage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: DealStage }) =>
      canadaLeadsService.updateStage(id, stage),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: canadaKeys.leadsRoot() })
      qc.invalidateQueries({ queryKey: canadaKeys.lead(vars.id) })
    },
  })
}

export function useUpdateCanadaLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Deal> }) =>
      canadaLeadsService.update(id, updates),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: canadaKeys.leadsRoot() })
      qc.invalidateQueries({ queryKey: canadaKeys.lead(vars.id) })
    },
  })
}

export function useDeleteCanadaLead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => canadaLeadsService.delete(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: canadaKeys.leadsRoot() })
      qc.invalidateQueries({ queryKey: canadaKeys.lead(id) })
    },
  })
}

// ── Realtime bridge ────────────────────────────────────────────────────────
// The existing Supabase realtime subscription pushes fresh deal lists
// directly. Bridge that into the query cache so every page using
// `useCanadaLeads` updates without polling.
export function useCanadaLeadsRealtime(repId: string | undefined) {
  const qc = useQueryClient()
  useEffect(() => {
    const channel = canadaLeadsService.subscribe(repId, (deals) => {
      qc.setQueryData(canadaKeys.leads(repId), deals)
    })
    return () => { canadaLeadsService.unsubscribe(channel) }
  }, [repId, qc])
}
