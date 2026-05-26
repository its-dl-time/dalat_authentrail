"use client";

import { useEffect, useRef } from "react";
import { io } from "socket.io-client";
import type { Socket } from "socket.io-client";

const SOCKET_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

// Connects to the Socket.io server and joins a place room.
// Handlers ref is updated every render so closures are never stale.
export function useSocket(
  placeId: string | undefined,
  handlers: Record<string, (data: unknown) => void>,
) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!placeId) return;

    const socket = io(SOCKET_URL, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    socket.emit("join:place", placeId);

    // Register all handlers via the ref so they see fresh state
    const events = Object.keys(handlersRef.current);
    for (const event of events) {
      socket.on(event, (data: unknown) => handlersRef.current[event]?.(data));
    }

    return () => {
      socket.emit("leave:place", placeId);
      socket.disconnect();
      socketRef.current = null;
    };
  }, [placeId]);

  return socketRef;
}
