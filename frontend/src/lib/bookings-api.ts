/**
 * Bookings API client — reservations and appointments.
 *
 * Wire format is snake_case (PostgREST all the way down); the UI works in
 * camelCase. Mapping happens here rather than in components so a column
 * rename touches one file.
 *
 * Times on the wire are always UTC ISO instants. The *label* a merchant reads
 * is computed server-side in their own timezone and shipped as `localLabel` —
 * the browser's timezone is irrelevant and must never be used to render a
 * booking time, because an owner checking tonight's book from an airport
 * would otherwise see every reservation shifted.
 */
import { getAuthHeaders } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

async function call<T>(
  path: string,
  opts: { method?: string; body?: unknown; params?: Record<string, string> } = {},
): Promise<T> {
  const url = new URL(`${API_BASE}/api/bookings${path}`, window.location.origin)
  Object.entries(opts.params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
  })
  const res = await fetch(url.toString(), {
    method: opts.method || 'GET',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(await getAuthHeaders()),
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new BookingsApiError(res.status, text)
  }
  return res.json() as Promise<T>
}

export class BookingsApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API ${status}: ${body}`)
    this.name = 'BookingsApiError'
  }
  /** 409 is the double-book collision, which the UI handles specifically. */
  get isSlotTaken() {
    return this.status === 409
  }
}

export type ResourceKind = 'table' | 'staff' | 'chair' | 'bay' | 'room'
export type BookingStatus =
  | 'confirmed' | 'seated' | 'completed' | 'cancelled' | 'no_show'

export interface Resource {
  id: string
  name: string
  kind: ResourceKind
  seats: number
  sortOrder: number
  active: boolean
}

export interface Service {
  id: string
  name: string
  description?: string
  durationMinutes: number
  bufferMinutes: number
  priceCents?: number | null
  minParty: number
  maxParty: number
  active: boolean
}

export interface HoursRow {
  weekday: number
  opensAt: string
  closesAt: string
  slotMinutes: number
}

export interface Booking {
  id: string
  resourceId: string
  serviceId?: string | null
  startsAt: string
  endsAt: string
  durationMinutes?: number | null
  partySize: number
  customerName: string
  customerPhone?: string | null
  customerEmail?: string | null
  notes?: string | null
  status: BookingStatus
  source: string
  confirmationCode: string
  provider?: string | null
}

export interface Slot {
  startsAt: string
  endsAt: string
  localLabel: string
  resourceId: string
  resourceName: string
  durationMinutes: number
}

export interface Connection {
  id: string
  provider: string
  status: 'pending' | 'connected' | 'error' | 'disabled'
  direction: 'read' | 'write' | 'both'
  lastSyncAt?: string | null
  lastError?: string | null
}

export interface AvailableProvider {
  key: string
  label: string
  summary: string
  readBusy: boolean
  writeBooking: boolean
  webhooks: boolean
}

export type WaitlistStatus =
  | 'waiting' | 'offered' | 'booked' | 'declined' | 'expired' | 'cancelled'

export interface WaitlistEntry {
  id: string
  customerName: string
  customerPhone: string
  partySize: number
  windowStart: string
  windowEnd: string
  status: WaitlistStatus
  notes?: string | null
  offeredAt?: string | null
  offerExpiresAt?: string | null
  offerCount: number
  /** Plain-English record of why this guest was ranked where they were. */
  rankReason?: string | null
  createdAt: string
}

const waitlistEntry = (w: any): WaitlistEntry => ({
  id: w.id,
  customerName: w.customer_name ?? '',
  customerPhone: w.customer_phone ?? '',
  partySize: w.party_size ?? 1,
  windowStart: w.window_start,
  windowEnd: w.window_end,
  status: w.status,
  notes: w.notes ?? null,
  offeredAt: w.offered_at ?? null,
  offerExpiresAt: w.offer_expires_at ?? null,
  offerCount: w.offer_count ?? 0,
  rankReason: w.rank_reason ?? null,
  createdAt: w.created_at,
})

export interface SquareService {
  serviceVariationId: string
  serviceVariationVersion: number
  name: string
  durationMinutes: number | null
}

export interface SquareTeamMember {
  teamMemberId: string
  displayName: string
  isBookable: boolean
}

export interface SquareOptions {
  /**
   * 'buyer' works on every Square plan and covers the whole booking loop.
   * 'seller' additionally lets us read bookings taken elsewhere, and requires
   * the merchant to pay for Appointments Plus or Premium.
   */
  accessLevel: 'buyer' | 'seller'
  bookingEnabled: boolean
  locationId: string
  services: SquareService[]
  teamMembers: SquareTeamMember[]
  defaultService: {
    serviceVariationId: string
    serviceVariationVersion: number
    teamMemberId: string
  } | null
}

export interface UnavailableTool {
  key: string
  label: string
  reason: string
  workaround: string
}

const resource = (r: any): Resource => ({
  id: r.id,
  name: r.name,
  kind: r.kind,
  seats: r.seats ?? 1,
  sortOrder: r.sort_order ?? 0,
  active: r.active !== false,
})

const service = (s: any): Service => ({
  id: s.id,
  name: s.name,
  description: s.description ?? undefined,
  durationMinutes: s.duration_minutes ?? 60,
  bufferMinutes: s.buffer_minutes ?? 0,
  priceCents: s.price_cents ?? null,
  minParty: s.min_party ?? 1,
  maxParty: s.max_party ?? 1,
  active: s.active !== false,
})

const booking = (b: any): Booking => ({
  id: b.id,
  resourceId: b.resource_id,
  serviceId: b.service_id ?? null,
  startsAt: b.starts_at,
  endsAt: b.ends_at,
  durationMinutes: b.duration_minutes ?? null,
  partySize: b.party_size ?? 1,
  customerName: b.customer_name ?? '',
  customerPhone: b.customer_phone ?? null,
  customerEmail: b.customer_email ?? null,
  notes: b.notes ?? null,
  status: b.status,
  source: b.source ?? 'phone',
  confirmationCode: b.confirmation_code ?? '',
  provider: b.provider ?? null,
})

const connection = (c: any): Connection => ({
  id: c.id,
  provider: c.provider,
  status: c.status,
  direction: c.direction,
  lastSyncAt: c.last_sync_at ?? null,
  lastError: c.last_error ?? null,
})

export const bookingsApi = {
  async listResources(merchantId: string): Promise<Resource[]> {
    const r = await call<{ resources: any[] }>(`/resources/${merchantId}`)
    return (r.resources || []).map(resource)
  },

  async createResource(input: {
    merchantId: string; name: string; kind: ResourceKind
    seats: number; sortOrder?: number
  }): Promise<Resource> {
    const r = await call<{ resource: any }>('/resources', {
      method: 'POST',
      body: {
        merchant_id: input.merchantId,
        name: input.name,
        kind: input.kind,
        seats: input.seats,
        sort_order: input.sortOrder ?? 0,
      },
    })
    return resource(r.resource)
  },

  async updateResource(id: string, patch: Partial<Resource>): Promise<Resource> {
    const r = await call<{ resource: any }>(`/resources/${id}`, {
      method: 'PATCH',
      body: {
        name: patch.name,
        seats: patch.seats,
        sort_order: patch.sortOrder,
        active: patch.active,
      },
    })
    return resource(r.resource)
  },

  async listServices(merchantId: string): Promise<Service[]> {
    const r = await call<{ services: any[] }>(`/services/${merchantId}`)
    return (r.services || []).map(service)
  },

  async createService(input: {
    merchantId: string; name: string; durationMinutes: number
    bufferMinutes?: number; minParty?: number; maxParty?: number
    resourceKind?: ResourceKind; priceCents?: number | null
  }): Promise<Service> {
    const r = await call<{ service: any }>('/services', {
      method: 'POST',
      body: {
        merchant_id: input.merchantId,
        name: input.name,
        duration_minutes: input.durationMinutes,
        buffer_minutes: input.bufferMinutes ?? 0,
        min_party: input.minParty ?? 1,
        max_party: input.maxParty ?? 1,
        resource_kind: input.resourceKind ?? null,
        price_cents: input.priceCents ?? null,
      },
    })
    return service(r.service)
  },

  async listHours(merchantId: string): Promise<HoursRow[]> {
    const r = await call<{ hours: any[] }>(`/hours/${merchantId}`)
    return (r.hours || []).map((h) => ({
      weekday: h.weekday,
      opensAt: String(h.opens_at || '').slice(0, 5),
      closesAt: String(h.closes_at || '').slice(0, 5),
      slotMinutes: h.slot_minutes ?? 15,
    }))
  },

  async replaceHours(merchantId: string, rows: HoursRow[]): Promise<HoursRow[]> {
    const r = await call<{ hours: any[] }>('/hours', {
      method: 'PUT',
      body: {
        merchant_id: merchantId,
        rows: rows.map((h) => ({
          weekday: h.weekday,
          opens_at: h.opensAt,
          closes_at: h.closesAt,
          slot_minutes: h.slotMinutes,
        })),
      },
    })
    return (r.hours || []).map((h) => ({
      weekday: h.weekday,
      opensAt: String(h.opens_at || '').slice(0, 5),
      closesAt: String(h.closes_at || '').slice(0, 5),
      slotMinutes: h.slot_minutes ?? 15,
    }))
  },

  async listBookings(
    merchantId: string, startIso: string, endIso: string,
    includeCancelled = false,
  ): Promise<Booking[]> {
    const r = await call<{ bookings: any[] }>(`/list/${merchantId}`, {
      params: {
        start: startIso,
        end: endIso,
        include_cancelled: String(includeCancelled),
      },
    })
    return (r.bookings || []).map(booking)
  },

  async availability(
    merchantId: string, day: string, partySize = 1,
  ): Promise<{ timezone: string; slots: Slot[] }> {
    const r = await call<{ timezone: string; slots: any[] }>(
      `/availability/${merchantId}`,
      { params: { day, party_size: String(partySize) } },
    )
    return {
      timezone: r.timezone,
      slots: (r.slots || []).map((s) => ({
        startsAt: s.starts_at,
        endsAt: s.ends_at,
        localLabel: s.local_label,
        resourceId: s.resource_id,
        resourceName: s.resource_name,
        durationMinutes: s.duration_minutes,
      })),
    }
  },

  async createBooking(input: {
    merchantId: string; startsAt: string; partySize: number
    customerName: string; customerPhone?: string; notes?: string
    serviceId?: string; source?: string
  }): Promise<Booking> {
    const r = await call<{ booking: any }>('/create', {
      method: 'POST',
      body: {
        merchant_id: input.merchantId,
        starts_at: input.startsAt,
        party_size: input.partySize,
        customer_name: input.customerName,
        customer_phone: input.customerPhone || null,
        notes: input.notes || null,
        service_id: input.serviceId || null,
        source: input.source || 'portal',
      },
    })
    return booking(r.booking)
  },

  async updateBooking(id: string, patch: {
    status?: BookingStatus; startsAt?: string; resourceId?: string
    partySize?: number; notes?: string
  }): Promise<Booking> {
    const r = await call<{ booking: any }>(`/${id}`, {
      method: 'PATCH',
      body: {
        status: patch.status,
        starts_at: patch.startsAt,
        resource_id: patch.resourceId,
        party_size: patch.partySize,
        notes: patch.notes,
      },
    })
    return booking(r.booking)
  },

  async listWaitlist(merchantId: string, status = 'waiting'): Promise<WaitlistEntry[]> {
    const r = await call<{ waitlist: any[] }>(`/waitlist/${merchantId}`, {
      params: { status },
    })
    return (r.waitlist || []).map(waitlistEntry)
  },

  async addToWaitlist(input: {
    merchantId: string; customerName: string; customerPhone: string
    partySize: number; windowStart: string; windowEnd: string
    minNoticeMinutes?: number; notes?: string
  }): Promise<WaitlistEntry> {
    const r = await call<{ entry: any }>('/waitlist', {
      method: 'POST',
      body: {
        merchant_id: input.merchantId,
        customer_name: input.customerName,
        customer_phone: input.customerPhone,
        party_size: input.partySize,
        window_start: input.windowStart,
        window_end: input.windowEnd,
        min_notice_minutes: input.minNoticeMinutes ?? 60,
        notes: input.notes || null,
      },
    })
    return waitlistEntry(r.entry)
  },

  async removeFromWaitlist(entryId: string) {
    return call(`/waitlist/${entryId}`, { method: 'DELETE' })
  },

  /** Offer a freed slot to the waitlist by hand — e.g. after a no-show. */
  async recoverSlot(merchantId: string, bookingId: string) {
    return call<{ offered: boolean; reason: string; candidates?: number }>(
      `/waitlist/${merchantId}/recover/${bookingId}`, { method: 'POST' })
  },

  async integrations(merchantId: string): Promise<{
    connections: Connection[]
    available: AvailableProvider[]
    unavailable: UnavailableTool[]
  }> {
    const r = await call<any>(`/integrations/${merchantId}`)
    return {
      connections: (r.connections || []).map(connection),
      available: (r.available || []).map((p: any) => ({
        key: p.key,
        label: p.label,
        summary: p.summary,
        readBusy: !!p.read_busy,
        writeBooking: !!p.write_booking,
        webhooks: !!p.webhooks,
      })),
      unavailable: r.unavailable || [],
    }
  },

  async connectIcsFeed(merchantId: string, url: string) {
    return call<{ connection: any; sync: any }>('/integrations/ics', {
      method: 'POST',
      body: { merchant_id: merchantId, url },
    })
  },

  /** Square Appointments: start OAuth. Returns the URL to send them to. */
  async squareAuthorizeUrl(merchantId: string, returnTo: string): Promise<string> {
    const r = await call<{ authorize_url: string }>('/square/authorize', {
      params: { merchant_id: merchantId, return_to: returnTo },
    })
    return r.authorize_url
  },

  async squareOptions(merchantId: string): Promise<SquareOptions> {
    const r = await call<any>(`/square/options/${merchantId}`)
    return {
      accessLevel: r.access_level === 'seller' ? 'seller' : 'buyer',
      bookingEnabled: !!r.booking_enabled,
      locationId: r.location_id || '',
      services: (r.services || []).map((s: any) => ({
        serviceVariationId: s.service_variation_id,
        serviceVariationVersion: s.service_variation_version,
        name: s.name || '',
        durationMinutes: s.duration_minutes ?? null,
      })),
      teamMembers: (r.team_members || []).map((t: any) => ({
        teamMemberId: t.team_member_id,
        displayName: t.display_name || '',
        isBookable: !!t.is_bookable,
      })),
      defaultService: r.default_service
        ? {
            serviceVariationId: r.default_service.service_variation_id,
            serviceVariationVersion: r.default_service.service_variation_version,
            teamMemberId: r.default_service.team_member_id,
          }
        : null,
    }
  },

  async saveSquareMapping(merchantId: string, defaultService: {
    serviceVariationId: string
    serviceVariationVersion: number
    teamMemberId: string
  }) {
    return call(`/square/options/${merchantId}`, {
      method: 'POST',
      body: {
        default_service: {
          service_variation_id: defaultService.serviceVariationId,
          service_variation_version: defaultService.serviceVariationVersion,
          team_member_id: defaultService.teamMemberId,
        },
      },
    })
  },

  async refreshSquare(merchantId: string) {
    return call(`/square/refresh/${merchantId}`, { method: 'POST' })
  },

  async enableFeed(merchantId: string): Promise<string> {
    const r = await call<{ feed_url: string }>(`/feed/${merchantId}/enable`, {
      method: 'POST',
    })
    return r.feed_url
  },
}
