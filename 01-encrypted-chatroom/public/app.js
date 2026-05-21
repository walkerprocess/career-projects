const joinPanel = document.querySelector("#joinPanel");
const chatPanel = document.querySelector("#chatPanel");
const joinButton = document.querySelector("#joinButton");
const nameInput = document.querySelector("#nameInput");
const roomInput = document.querySelector("#roomInput");
const passInput = document.querySelector("#passInput");
const roomTitle = document.querySelector("#roomTitle");
const statusLabel = document.querySelector("#status");
const messages = document.querySelector("#messages");
const form = document.querySelector("#messageForm");
const messageInput = document.querySelector("#messageInput");
const clearButton = document.querySelector("#clearButton");

let socket;
let cryptoKey;
let displayName;

roomInput.value = `room-${randomToken(9)}`;

joinButton.addEventListener("click", async () => {
  displayName = nameInput.value.trim() || "Anonymous";
  const room = roomInput.value.trim();
  const passphrase = passInput.value;
  if (!room || passphrase.length < 8) {
    alert("Use a room name and a passphrase of at least 8 characters.");
    return;
  }
  if (!globalThis.isSecureContext || !crypto.subtle) {
    alert("Browser encryption requires HTTPS, localhost, or another secure browser context.");
    return;
  }

  cryptoKey = await deriveKey(passphrase, room);
  const roomId = await hashRoomId(room);
  socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`);
  socket.addEventListener("open", () => {
    socket.send(JSON.stringify({ type: "join", roomId }));
    statusLabel.textContent = "connected";
  });
  socket.addEventListener("message", handleSocketMessage);
  socket.addEventListener("close", () => {
    statusLabel.textContent = "disconnected";
  });

  roomTitle.textContent = room;
  joinPanel.classList.add("hidden");
  chatPanel.classList.remove("hidden");
  messageInput.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  const encrypted = await encryptMessage({ sender: displayName, text }, cryptoKey);
  socket.send(JSON.stringify({ type: "ciphertext", ...encrypted }));
  messageInput.value = "";
});

clearButton.addEventListener("click", () => {
  messages.replaceChildren();
});

async function handleSocketMessage(event) {
  const message = JSON.parse(event.data);
  if (message.type === "system") {
    appendMessage("System", message.text, false);
    return;
  }
  if (message.type !== "ciphertext") return;

  try {
    const envelope = await decryptMessage(message, cryptoKey);
    appendMessage(envelope.sender, envelope.text, envelope.sender === displayName);
  } catch {
    appendMessage("System", "Could not decrypt a message. Passphrase or room may differ.", false);
  }
}

async function deriveKey(passphrase, room) {
  const enc = new TextEncoder();
  const baseKey = await crypto.subtle.importKey("raw", enc.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: enc.encode(`encrypted-chatroom:${room}`),
      iterations: 250000,
      hash: "SHA-256"
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

async function hashRoomId(room) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`room-id:${room}`));
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

async function encryptMessage(envelope, key) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const bytes = new TextEncoder().encode(JSON.stringify(envelope));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, bytes);
  return {
    iv: toBase64(iv),
    ciphertext: toBase64(new Uint8Array(ciphertext))
  };
}

async function decryptMessage(message, key) {
  const iv = fromBase64(message.iv);
  const ciphertext = fromBase64(message.ciphertext);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ciphertext);
  return JSON.parse(new TextDecoder().decode(plain));
}

function appendMessage(sender, text, mine) {
  const item = document.createElement("li");
  item.className = mine ? "mine" : "";
  item.textContent = `${sender}: ${text}`;
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
}

function toBase64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function fromBase64(value) {
  return Uint8Array.from(atob(value), c => c.charCodeAt(0));
}

function randomToken(bytes) {
  const values = crypto.getRandomValues(new Uint8Array(bytes));
  return [...values].map(value => value.toString(16).padStart(2, "0")).join("");
}
