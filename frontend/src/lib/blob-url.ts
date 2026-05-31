// Open a Blob in a new tab without leaking its object URL.
// The new tab needs the URL alive long enough to start its first paint, so we
// schedule the revoke 60s later — generous and harmless if the tab is already
// loaded. If the user closes the source page before the timer fires, the URL
// is GC'd anyway.
export function openBlobInNewTab(blob: Blob): void {
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
