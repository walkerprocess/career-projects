import http from "node:http";
import https from "node:https";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import selfsigned from "selfsigned";
import { WebSocketServer } from "ws";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, "public");
const cliOptions = Object.fromEntries(
  process.argv.slice(2)
    .filter(arg => arg.startsWith("--") && arg.includes("="))
    .map(arg => {
      const [key, ...valueParts] = arg.slice(2).split("=");
      return [key, valueParts.join("=")];
    })
);
const preferredPort = Number(cliOptions.port || process.env.PORT || 3000);
const shouldUseExactPort = Boolean(cliOptions.port || process.env.PORT);
const host = cliOptions.host || process.env.HOST || "127.0.0.1";
const useHttps = cliOptions.https === "1" || cliOptions.https === "true" || process.env.HTTPS === "1";
const maxMessageBytes = 64 * 1024;
const emptyRoomTtlMs = 30_000;

function createServer() {
  const handler = async (req, res) => {
    const urlPath = req.url === "/" ? "/index.html" : req.url;
    const safePath = path.normalize(urlPath).replace(/^(\.\.[/\\])+/, "");
    const filePath = path.join(publicDir, safePath);

    if (!filePath.startsWith(publicDir)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    try {
      const ext = path.extname(filePath);
      const type = ext === ".css" ? "text/css; charset=utf-8" : ext === ".js" ? "text/javascript; charset=utf-8" : "text/html; charset=utf-8";
      const file = await fs.readFile(filePath);
      res.writeHead(200, {
        "Content-Type": type,
        "Cache-Control": "no-store, max-age=0",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self'; connect-src 'self' ws: wss:; script-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
      });
      res.end(file);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  };

  if (!useHttps) return http.createServer(handler);

  return https.createServer(createEphemeralCertificate(), handler);
}

function createEphemeralCertificate() {
  const altNames = [
    { type: 2, value: "localhost" },
    { type: 7, ip: "127.0.0.1" },
    ...privateIpv4Addresses().map(ip => ({ type: 7, ip }))
  ];
  const pems = selfsigned.generate(
    [{ name: "commonName", value: "Encrypted Chatroom Local Private Relay" }],
    {
      days: 1,
      keySize: 2048,
      algorithm: "sha256",
      extensions: [{ name: "subjectAltName", altNames }]
    }
  );

  return { key: pems.private, cert: pems.cert };
}

function privateIpv4Addresses() {
  return Object.values(os.networkInterfaces())
    .flat()
    .filter(details => details && details.family === "IPv4" && !details.internal)
    .map(details => details.address);
}

const rooms = new Map();

function getOrCreateRoom(roomId) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, { sockets: new Set(), cleanupTimer: null });
  }
  const room = rooms.get(roomId);
  if (room.cleanupTimer) {
    clearTimeout(room.cleanupTimer);
    room.cleanupTimer = null;
  }
  return room;
}

function removeFromRoom(roomId, socket) {
  const room = rooms.get(roomId);
  if (!room) return;
  room.sockets.delete(socket);
  if (room.sockets.size === 0) {
    room.cleanupTimer = setTimeout(() => rooms.delete(roomId), emptyRoomTtlMs);
  }
}

function attachWebSocketServer(server) {
  const wss = new WebSocketServer({ server, maxPayload: maxMessageBytes });

  wss.on("connection", (socket) => {
    let currentRoom = null;

    socket.on("message", (raw) => {
      if (raw.byteLength > maxMessageBytes) return;
      let message;
      try {
        message = JSON.parse(raw.toString());
      } catch {
        return;
      }

      if (message.type === "join" && typeof message.roomId === "string" && /^[a-f0-9]{64}$/.test(message.roomId)) {
        if (currentRoom) removeFromRoom(currentRoom, socket);
        currentRoom = message.roomId;
        getOrCreateRoom(currentRoom).sockets.add(socket);
        socket.send(JSON.stringify({ type: "system", text: "Joined private relay. No server-side message history is kept." }));
        return;
      }

      if (message.type === "ciphertext" && currentRoom && typeof message.iv === "string" && typeof message.ciphertext === "string") {
        const room = rooms.get(currentRoom);
        if (!room) return;
        const payload = JSON.stringify({
          type: "ciphertext",
          iv: message.iv,
          ciphertext: message.ciphertext
        });
        for (const peer of room.sockets) {
          if (peer.readyState === peer.OPEN) peer.send(payload);
        }
      }
    });

    socket.on("close", () => {
      if (currentRoom) removeFromRoom(currentRoom, socket);
    });
  });
}

function start(port, attemptsLeft = 20) {
  const server = createServer();

  server.once("error", (error) => {
    if (error.code === "EADDRINUSE" && !shouldUseExactPort && attemptsLeft > 0) {
      console.warn(`Port ${port} is already in use; trying ${port + 1}...`);
      start(port + 1, attemptsLeft - 1);
      return;
    }

    console.error(`Could not start encrypted chatroom on port ${port}.`);
    console.error(error);
    process.exitCode = 1;
  });

  server.listen(port, host, () => {
    attachWebSocketServer(server);
    const protocol = useHttps ? "https" : "http";
    const localUrl = `${protocol}://localhost:${port}`;
    const networkUrl = host === "0.0.0.0" ? `${protocol}://<your-ip>:${port}` : `${protocol}://${host}:${port}`;
    console.log(`Encrypted chatroom running at ${localUrl}`);
    console.log(`Bind address: ${host}`);
    console.log(`Network URL: ${networkUrl}`);
    if (useHttps) {
      console.log("HTTPS uses an ephemeral self-signed certificate. Accept the browser warning only for people you trust.");
    }
  });
}

start(preferredPort);
