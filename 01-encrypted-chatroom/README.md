# Encrypted Chatroom

End-to-end encrypted browser chatroom for demonstrating practical security, full-stack product thinking, and clear technical documentation.

## Career angle

This project supports:

- CMU MSIS narrative: cryptography, secure systems, threat modeling
- Software/product analyst roles: real-time product with clear user flows
- BI/security-adjacent roles: shows you can explain tradeoffs, not just use tools

## MVP

- Room-based chat using WebSocket relay
- Messages encrypted in the browser before being sent
- Server stores and relays ciphertext only
- Shared room passphrase derives an AES-GCM key with PBKDF2
- Security notes document what the app does and does not protect

## Run

```bash
npm install
npm start
```

Then open `http://localhost:3000` in two browser tabs, join the same room with the same passphrase, and send messages.

## Private Network Mode

For another device or another network, run the HTTPS relay:

```bash
npm run start:private
```

On the same Wi-Fi, share your computer's network URL, for example:

```text
https://192.168.219.109:3000
```

For a different network, your router must forward TCP port `3000` to this computer, or the app must run on a public server. Without one of those, people outside your network cannot reach your laptop. The private mode uses a one-day self-signed HTTPS certificate, so browsers will show a warning the first time. Accept it only when you are sure the address is yours.

Privacy design:

- Server has no message database, no room list endpoint, and no chat history.
- The server only keeps active room sockets in memory.
- Room names are hashed before they reach the server.
- Sender name and message text are encrypted together in the browser.
- Closing the server clears active room state.

No app can make an absolute "nobody can ever find anything" promise. Routers, ISPs, browsers, OS logs, screenshots, and clipboard history can still expose connection metadata or local traces. For sensitive use, share the room name and passphrase out of band, use private browsing, close the tab when done, and stop the server.

## Resume bullet draft

Built an end-to-end encrypted WebSocket chatroom using browser Web Crypto APIs, AES-GCM, and PBKDF2, documenting the threat model and security limitations for a production-style secure messaging prototype.
