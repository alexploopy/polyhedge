import { HedgeRequest, HedgeResponse, SSEEvent } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate hedge recommendations (synchronous).
 */
export async function generateHedge(request: HedgeRequest): Promise<HedgeResponse> {
  const response = await fetch(`${API_URL}/api/hedge`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate hedge');
  }

  return response.json();
}

/**
 * Generate hedge recommendations with streaming progress updates.
 */
export async function generateHedgeStream(
  request: HedgeRequest,
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/hedge/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to start streaming');
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No response body');
  }

  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log('[API] Stream complete. Buffer size:', buffer.length);
        // Process any remaining buffer content
        if (buffer.trim()) {
          console.log('[API] Processing remaining buffer');
          // Split by double newline (handles \n\n or \r\n\r\n)
          const lines = buffer.split(/\r\n\r\n|\n\n/);
          console.log(`[API] Split into ${lines.length} events`);

          for (const line of lines) {
            if (!line.trim()) continue;
            const eventMatch = line.match(/^event: (.+)$/m);
            const dataMatch = line.match(/^data: (.+)$/m);

            if (eventMatch && dataMatch) {
              console.log('[API] Parsed final event:', eventMatch[1]);
              onEvent({
                type: eventMatch[1] as SSEEvent['type'],
                data: JSON.parse(dataMatch[1]),
              });
            }
          }
        }
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      console.log('[API] Received chunk size:', chunk.length, 'Total buffer:', buffer.length);

      // Process complete SSE messages
      // Split by double newline (handles \n\n or \r\n\r\n)
      const lines = buffer.split(/\r\n\r\n|\n\n/);

      // Keep the last partial chunk in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;

        const eventMatch = line.match(/^event: (.+)$/m);
        const dataMatch = line.match(/^data: (.+)$/m);

        if (eventMatch && dataMatch) {
          const eventType = eventMatch[1];
          console.log('[API] Parsed event:', eventType);
          const eventData = JSON.parse(dataMatch[1]);

          onEvent({
            type: eventType as SSEEvent['type'],
            data: eventData,
          });
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error('API is not healthy');
  }

  return response.json();
}
