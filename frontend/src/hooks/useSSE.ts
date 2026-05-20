/**
 * useSSE — Subscribe to a server-sent events stream for a session.
 *
 * Manages EventSource lifecycle (open → messages → close/error).
 * Accumulates events in a list. Signals completion when STREAM_CLOSED
 * or ANALYSIS_COMPLETED is received.
 *
 * Usage:
 *   const { events, isConnected, isComplete } = useSSE(sessionId);
 */
import { useEffect, useRef, useCallback, useState, useLayoutEffect } from "react";
import type { WorkflowEvent, WorkflowEventType } from "@/types";

interface UseSSEOptions {
  /** Called for every event received */
  onEvent?: (event: WorkflowEvent) => void;
  /** Called when the stream closes gracefully */
  onComplete?: () => void;
  /** Called on EventSource error */
  onError?: (err: Event) => void;
  /** Max events to keep in memory (oldest dropped) */
  maxEvents?: number;
}

interface UseSSEResult {
  events: WorkflowEvent[];
  isConnected: boolean;
  isComplete: boolean;
  error: string | null;
  /** Manually disconnect */
  disconnect: () => void;
}

const TERMINAL_EVENTS: WorkflowEventType[] = [
  "STREAM_CLOSED",
  "ANALYSIS_COMPLETED",
  "ANALYSIS_FAILED",
  "REPLAY_COMPLETE",
];

export function useSSE(
  sessionId: string | null | undefined,
  options: UseSSEOptions = {}
): UseSSEResult {
  const { onEvent, onComplete, onError, maxEvents = 500 } = options;

  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);

  // Store callbacks in refs so they never appear in the effect dependency array.
  // This prevents inline arrow functions in the caller from re-triggering the
  // effect (and re-mounting the EventSource) on every render.
  const onEventRef    = useRef(onEvent);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef    = useRef(onError);
  useLayoutEffect(() => { onEventRef.current    = onEvent;    });
  useLayoutEffect(() => { onCompleteRef.current = onComplete; });
  useLayoutEffect(() => { onErrorRef.current    = onError;    });

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Only re-run when sessionId or maxEvents changes — NOT when callbacks change.
  useEffect(() => {
    if (!sessionId) return;

    // Reset state for new session
    setEvents([]);
    setIsComplete(false);
    setError(null);

    const url = `/api/v1/stream/${sessionId}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.onmessage = (e: MessageEvent<string>) => {
      try {
        const event = JSON.parse(e.data) as WorkflowEvent;

        setEvents((prev) => {
          const next = [...prev, event];
          return next.length > maxEvents ? next.slice(-maxEvents) : next;
        });

        onEventRef.current?.(event);

        if (TERMINAL_EVENTS.includes(event.event_type)) {
          setIsComplete(true);
          setIsConnected(false);
          es.close();
          onCompleteRef.current?.();
        }
      } catch {
        // Ignore malformed events
      }
    };

    es.onerror = (e) => {
      setIsConnected(false);
      setError("Connection lost. Attempting to reconnect…");
      onErrorRef.current?.(e);
      // EventSource auto-reconnects on error; we just track state
    };

    return () => {
      es.close();
      esRef.current = null;
      // Do NOT call setIsConnected here — that setter call during cleanup
      // was the second half of the infinite-loop trigger.
    };
  }, [sessionId, maxEvents]); // ← callbacks intentionally omitted

  return { events, isConnected, isComplete, error, disconnect };
}

/** Filter events by agent name */
export function filterEventsByAgent(
  events: WorkflowEvent[],
  agentName: string
): WorkflowEvent[] {
  return events.filter((e) => e.agent_name === agentName);
}

/** Get the latest ANALYSIS_PROGRESS event for an agent */
export function getAgentProgress(
  events: WorkflowEvent[],
  agentName: string
): number {
  const agentEvents = filterEventsByAgent(events, agentName)
    .filter((e) => e.event_type === "ANALYSIS_PROGRESS");
  if (agentEvents.length === 0) return 0;
  return (agentEvents[agentEvents.length - 1].progress as number) ?? 0;
}
