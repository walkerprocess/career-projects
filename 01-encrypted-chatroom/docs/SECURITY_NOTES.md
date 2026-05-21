# Security Notes

## What is protected

- Message content is encrypted before it leaves the browser.
- Sender names and message content are encrypted before they leave the browser.
- Room names are hashed before they reach the server.
- The server receives only active-room hashes, `iv`, and `ciphertext` values.
- AES-GCM provides confidentiality and integrity for each message.
- PBKDF2 slows down brute-force attempts against weak passphrases.
- HTTP responses use no-store headers so the app shell is not intentionally cached.

## What is not protected yet

- Message timing and IP metadata are visible to the server and network path.
- Anyone with the room name and passphrase can read the room.
- There is no identity verification, so users can impersonate display names if they know the room and passphrase.
- Messages are not persisted, audited, or recoverable.
- Browser history, screenshots, clipboard history, OS logs, router logs, and ISP metadata are outside the app's control.

## Next security upgrades

1. Replace shared passphrase with ECDH key exchange plus QR/fingerprint verification.
2. Add per-user signing keys so display names cannot be spoofed.
3. Add encrypted local message history using IndexedDB.
4. Add automated browser tests with Playwright.
