import { Server as SocketServer } from "socket.io";
import type { Server as HttpServer } from "http";
import { env } from "./env";

let io: SocketServer | null = null;

export function initSocket(httpServer: HttpServer): SocketServer {
  io = new SocketServer(httpServer, {
    cors: { origin: env.CORS_ORIGIN, credentials: true },
    transports: ["websocket", "polling"],
  });

  io.on("connection", (socket) => {
    socket.on("join:place",  (placeId: string) => socket.join(`place:${placeId}`));
    socket.on("leave:place", (placeId: string) => socket.leave(`place:${placeId}`));
  });

  return io;
}

// Broadcast a new question or answer to all clients watching a place
export function emitToPlace(placeId: string, event: string, data: unknown): void {
  io?.to(`place:${placeId}`).emit(event, data);
}
