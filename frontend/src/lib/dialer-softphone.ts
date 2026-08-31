// Softphone facade for the SR Auto Dialer.
//
// Two implementations behind one event contract:
//   * TelnyxSoftphone — real WebRTC via @telnyx/webrtc (dynamic import), logged
//     in with a backend-minted on-demand telephony-credential token.
//   * SimSoftphone — a timer-driven state walk for previews and for installs
//     where TELNYX_WEBRTC_CONNECTION_ID isn't configured yet. Places NO
//     traffic anywhere; the UI badges the mode unmistakably.
//
// Event order both implementations guarantee:
//   dialing → ringing → (answered → ended) | (ended with cause)

export type SoftphoneEvent =
  | { type: 'dialing' }
  | { type: 'ringing' }
  | { type: 'answered' }
  | { type: 'ended'; cause: 'hangup' | 'remote_hangup' | 'no_answer' | 'busy' | 'failed' }

export type SoftphoneListener = (ev: SoftphoneEvent) => void

export interface Softphone {
  readonly mode: 'sim' | 'webrtc'
  dial(destinationE164: string): Promise<void>
  hangup(): void
  setMuted(muted: boolean): void
  destroy(): void
}

// ── SIM ───────────────────────────────────────────────────────────────────────

export class SimSoftphone implements Softphone {
  readonly mode = 'sim' as const
  private timers: ReturnType<typeof setTimeout>[] = []
  private inCall = false

  constructor(private listener: SoftphoneListener) {}

  async dial(_destinationE164: string): Promise<void> {
    this.clearTimers()
    this.inCall = true
    this.listener({ type: 'dialing' })
    this.timers.push(setTimeout(() => {
      if (!this.inCall) return
      this.listener({ type: 'ringing' })
      // Simulated outcomes so the whole disposition flow is exercisable:
      // ~65% answer after 3-7s of ringing, ~25% ring out, ~10% busy.
      const roll = Math.random()
      if (roll < 0.65) {
        this.timers.push(setTimeout(() => {
          if (this.inCall) this.listener({ type: 'answered' })
        }, 3000 + Math.random() * 4000))
      } else if (roll < 0.9) {
        this.timers.push(setTimeout(() => {
          if (this.inCall) this.end('no_answer')
        }, 8000 + Math.random() * 6000))
      } else {
        this.timers.push(setTimeout(() => {
          if (this.inCall) this.end('busy')
        }, 1500 + Math.random() * 1500))
      }
    }, 900))
  }

  hangup(): void {
    if (this.inCall) this.end('hangup')
  }

  setMuted(_muted: boolean): void { /* nothing to mute in sim */ }

  destroy(): void {
    this.inCall = false
    this.clearTimers()
  }

  private end(cause: 'hangup' | 'no_answer' | 'busy') {
    this.inCall = false
    this.clearTimers()
    this.listener({ type: 'ended', cause })
  }

  private clearTimers() {
    this.timers.forEach(clearTimeout)
    this.timers = []
  }
}

// ── Telnyx WebRTC ─────────────────────────────────────────────────────────────

export class TelnyxSoftphone implements Softphone {
  readonly mode = 'webrtc' as const
  private client: any = null
  private call: any = null
  private ready: Promise<void>
  private answered = false
  // The SDK only plays inbound audio through a media element handed to it via
  // remoteElement — without one the far end hears the rep but the rep hears
  // nothing.
  private remoteAudio: HTMLAudioElement

  constructor(
    private listener: SoftphoneListener,
    loginToken: string,
    private callerNumber: string,
  ) {
    this.remoteAudio = document.createElement('audio')
    this.remoteAudio.autoplay = true
    this.remoteAudio.style.display = 'none'
    document.body.appendChild(this.remoteAudio)
    this.ready = this.connect(loginToken)
  }

  private async connect(loginToken: string): Promise<void> {
    const { TelnyxRTC } = await import('@telnyx/webrtc')
    this.client = new TelnyxRTC({ login_token: loginToken })
    this.client.remoteElement = this.remoteAudio
    this.client.on('telnyx.notification', (notification: any) => {
      if (notification?.type !== 'callUpdate' || !notification.call) return
      this.call = notification.call
      const state: string = notification.call.state
      if (state === 'trying' || state === 'requesting') {
        this.listener({ type: 'dialing' })
      } else if (state === 'ringing' || state === 'early') {
        this.listener({ type: 'ringing' })
      } else if (state === 'active') {
        this.answered = true
        // dial() runs off a click, so this play() sits inside a user gesture
        // chain; the catch covers a browser that still refuses autoplay.
        this.remoteAudio.play().catch(() => {})
        this.listener({ type: 'answered' })
      } else if (state === 'hangup' || state === 'destroy') {
        const cause = this.answered ? 'remote_hangup' : 'no_answer'
        this.answered = false
        this.listener({ type: 'ended', cause })
      }
    })
    await new Promise<void>((resolve, reject) => {
      this.client.on('telnyx.ready', () => resolve())
      this.client.on('telnyx.error', (err: unknown) => reject(err))
      this.client.connect()
    })
  }

  async dial(destinationE164: string): Promise<void> {
    await this.ready
    this.answered = false
    this.call = this.client.newCall({
      destinationNumber: destinationE164,
      callerNumber: this.callerNumber,
      remoteElement: this.remoteAudio,
      audio: true,
      video: false,
    })
    this.listener({ type: 'dialing' })
  }

  hangup(): void {
    try { this.call?.hangup() } catch { /* already down */ }
  }

  setMuted(muted: boolean): void {
    try { muted ? this.call?.muteAudio() : this.call?.unmuteAudio() } catch { /* no active call */ }
  }

  destroy(): void {
    try { this.call?.hangup() } catch { /* already down */ }
    try { this.client?.disconnect() } catch { /* already down */ }
    this.remoteAudio.srcObject = null
    this.remoteAudio.remove()
    this.client = null
    this.call = null
  }
}

/** Build the right softphone for this install (backend decides the mode). */
export async function createSoftphone(
  listener: SoftphoneListener,
  fetchToken: () => Promise<{ mode: 'sim' | 'webrtc'; token?: string; caller_id: string }>,
): Promise<Softphone> {
  try {
    const cfg = await fetchToken()
    if (cfg.mode === 'webrtc' && cfg.token) {
      return new TelnyxSoftphone(listener, cfg.token, cfg.caller_id)
    }
  } catch {
    // Token mint failed — fall through to SIM so the tab stays usable.
  }
  return new SimSoftphone(listener)
}
