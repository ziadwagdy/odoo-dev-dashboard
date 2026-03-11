export interface SSEOptions {
  onMessage: (data: unknown) => void
  onDone?: () => void
  onError?: () => void
}

export function openSSE(url: string, opts: SSEOptions): () => void {
  const source = new EventSource(url)
  source.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data)
      opts.onMessage(data)
      if ((data as Record<string, unknown>).done) {
        source.close()
        opts.onDone?.()
      }
    } catch {}
  }
  source.onerror = () => {
    opts.onError?.()
  }
  return () => source.close()
}
