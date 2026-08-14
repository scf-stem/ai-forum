"use client";

import { apiPost } from "./api";

function sessionId(): string {
  const key = "forum_session_id";
  let value = window.sessionStorage.getItem(key);
  if (!value) {
    value = crypto.randomUUID();
    window.sessionStorage.setItem(key, value);
  }
  return value;
}

export function trackEvents(events: Array<{ eventName: string; postId?: string; boardId?: string; properties?: Record<string, unknown> }>) {
  if (typeof window === "undefined" || events.length === 0) return;
  const occurredAt = new Date().toISOString();
  apiPost("/api/events/batch", { events: events.map((event) => ({
    event_id: crypto.randomUUID(), event_name: event.eventName,
    session_id: sessionId(), post_id: event.postId, board_id: event.boardId,
    properties: event.properties || {}, occurred_at: occurredAt,
  })) }).catch(() => undefined);
}
