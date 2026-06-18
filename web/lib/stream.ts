import type { AgentStep, ConciergeResult } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface StreamHandlers {
  onStep?: (step: AgentStep) => void;
  onResult?: (result: ConciergeResult) => void;
  onError?: (err: unknown) => void;
  signal?: AbortSignal;
}

/**
 * Consumes the POST SSE stream from /api/concierge/stream. EventSource only
 * speaks GET, so we read the fetch body manually and split on the SSE
 * record separator.
 */
export async function streamConcierge(
  message: string,
  city: string | undefined,
  { onStep, onResult, onError, signal }: StreamHandlers,
): Promise<void> {
  try {
    const res = await fetch(`${BASE}/api/concierge/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, city }),
      signal,
    });
    if (!res.body) throw new Error("no response stream");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const record = buffer.slice(0, sep).trim();
        buffer = buffer.slice(sep + 2);
        if (!record.startsWith("data:")) continue;
        const payload = record.slice(5).trim();
        if (payload === "[DONE]") return;
        const event = JSON.parse(payload);
        if (event.type === "step") onStep?.(event as AgentStep);
        else if (event.type === "result") onResult?.(event as ConciergeResult);
        else if (event.type === "error") {
          onError?.(new Error(event.message ?? "concierge error"));
          return;
        }
      }
    }
  } catch (err) {
    if ((err as Error)?.name !== "AbortError") onError?.(err);
  }
}
