const DB_NAME = "sbu-community-chat-keys";
const DB_VERSION = 1;
const DEVICE_STORE = "devices";
const CONVERSATION_KEY_STORE = "conversation-keys";
const conversationKeyCache = new Map<string, ConversationChatKey[]>();
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const rsaAlgorithm: RsaHashedKeyGenParams = {
  name: "RSA-OAEP",
  modulusLength: 3072,
  publicExponent: new Uint8Array([1, 0, 1]),
  hash: "SHA-256",
};

export interface ChatDeviceIdentity {
  deviceId: string;
  publicKey: string;
  privateKey: CryptoKey;
}

export interface ConversationChatKey {
  keyId: string;
  key: CryptoKey;
}

interface StoredDevice extends ChatDeviceIdentity {
  id: string;
}

interface StoredConversationKey extends ConversationChatKey {
  id: string;
  userId: string;
  conversationId: string;
}

export interface EncryptedMessage {
  content: string;
  keyId: string;
}

export function isEncryptedChatContent(content: string): boolean {
  return content.startsWith("e2ee:v1:");
}

function openKeyDatabase(): Promise<IDBDatabase> {
  if (!globalThis.crypto?.subtle || !globalThis.indexedDB) {
    throw new Error("End-to-end encryption requires a modern browser with secure storage.");
  }
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(DEVICE_STORE)) {
        database.createObjectStore(DEVICE_STORE, { keyPath: "id" });
      }
      if (!database.objectStoreNames.contains(CONVERSATION_KEY_STORE)) {
        database.createObjectStore(CONVERSATION_KEY_STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open encrypted key storage."));
  });
}

async function getRecord<T>(storeName: string, id: string): Promise<T | undefined> {
  const database = await openKeyDatabase();
  return new Promise((resolve, reject) => {
    const request = database.transaction(storeName, "readonly").objectStore(storeName).get(id);
    request.onsuccess = () => {
      database.close();
      resolve(request.result as T | undefined);
    };
    request.onerror = () => {
      database.close();
      reject(request.error ?? new Error("Could not read encrypted key storage."));
    };
  });
}

async function putRecord(storeName: string, value: object): Promise<void> {
  const database = await openKeyDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, "readwrite");
    transaction.objectStore(storeName).put(value);
    transaction.oncomplete = () => {
      database.close();
      resolve();
    };
    transaction.onerror = () => {
      database.close();
      reject(transaction.error ?? new Error("Could not persist encrypted keys."));
    };
    transaction.onabort = () => {
      database.close();
      reject(transaction.error ?? new Error("Encrypted key storage was interrupted."));
    };
  });
}

async function getConversationKeys(userId: string, conversationId: string): Promise<ConversationChatKey[]> {
  const cacheKey = `${userId}:${conversationId}`;
  const cached = conversationKeyCache.get(cacheKey);
  if (cached) return cached;
  const database = await openKeyDatabase();
  return new Promise((resolve, reject) => {
    const request = database.transaction(CONVERSATION_KEY_STORE, "readonly")
      .objectStore(CONVERSATION_KEY_STORE).getAll();
    request.onsuccess = () => {
      database.close();
      const keys = (request.result as StoredConversationKey[])
        .filter((entry) => entry.userId === userId && entry.conversationId === conversationId)
        .map(({ keyId, key }) => ({ keyId, key }));
      conversationKeyCache.set(cacheKey, keys);
      resolve(keys);
    };
    request.onerror = () => {
      database.close();
      reject(request.error ?? new Error("Could not read conversation keys."));
    };
  });
}

function toBase64(bytes: ArrayBuffer | Uint8Array): string {
  const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let binary = "";
  for (let offset = 0; offset < data.length; offset += 0x8000) {
    binary += String.fromCharCode(...data.subarray(offset, Math.min(offset + 0x8000, data.length)));
  }
  return btoa(binary);
}

function fromBase64(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  return buffer;
}

function storageId(userId: string, conversationId: string, keyId: string): string {
  return `${userId}:${conversationId}:${keyId}`;
}

export async function getOrCreateDeviceIdentity(userId: string): Promise<ChatDeviceIdentity> {
  const localStorageKey = `sbu-chat-device:${userId}`;
  let deviceId = localStorage.getItem(localStorageKey);
  if (deviceId) {
    const stored = await getRecord<StoredDevice>(DEVICE_STORE, `${userId}:${deviceId}`);
    if (stored) return stored;
  }

  deviceId = crypto.randomUUID();
  const generated = await crypto.subtle.generateKey(rsaAlgorithm, true, ["encrypt", "decrypt"]);
  const [publicBytes, privateBytes] = await Promise.all([
    crypto.subtle.exportKey("spki", generated.publicKey),
    crypto.subtle.exportKey("pkcs8", generated.privateKey),
  ]);
  const privateKey = await crypto.subtle.importKey("pkcs8", privateBytes, rsaAlgorithm, false, ["decrypt"]);
  new Uint8Array(privateBytes).fill(0);
  const identity: ChatDeviceIdentity = {
    deviceId,
    publicKey: toBase64(publicBytes),
    privateKey,
  };
  await putRecord(DEVICE_STORE, { ...identity, id: `${userId}:${deviceId}` });
  localStorage.setItem(localStorageKey, deviceId);
  return identity;
}

export async function getConversationKeysForUser(
  userId: string,
  conversationId: string,
): Promise<ConversationChatKey[]> {
  return getConversationKeys(userId, conversationId);
}

export async function createConversationKey(
  userId: string,
  conversationId: string,
): Promise<ConversationChatKey> {
  const keyId = crypto.randomUUID();
  const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
  const entry: StoredConversationKey = {
    id: storageId(userId, conversationId, keyId),
    userId,
    conversationId,
    keyId,
    key,
  };
  await putRecord(CONVERSATION_KEY_STORE, entry);
  conversationKeyCache.set(`${userId}:${conversationId}`, [
    ...(await getConversationKeys(userId, conversationId)),
    { keyId, key },
  ]);
  return { keyId, key };
}

export async function unwrapConversationKey(
  userId: string,
  conversationId: string,
  keyId: string,
  wrappedKey: string,
  privateKey: CryptoKey,
): Promise<ConversationChatKey> {
  const rawKey = await crypto.subtle.decrypt(
    { name: "RSA-OAEP", label: encoder.encode(`sbu-chat-key:${conversationId}:${keyId}`) },
    privateKey,
    toArrayBuffer(fromBase64(wrappedKey)),
  );
  const key = await crypto.subtle.importKey("raw", rawKey, "AES-GCM", true, ["encrypt", "decrypt"]);
  new Uint8Array(rawKey).fill(0);
  await putRecord(CONVERSATION_KEY_STORE, {
    id: storageId(userId, conversationId, keyId),
    userId,
    conversationId,
    keyId,
    key,
  } satisfies StoredConversationKey);
  const keys = await getConversationKeys(userId, conversationId);
  if (!keys.some((entry) => entry.keyId === keyId)) {
    conversationKeyCache.set(`${userId}:${conversationId}`, [...keys, { keyId, key }]);
  }
  return { keyId, key };
}

export async function wrapConversationKey(
  conversationId: string,
  entry: ConversationChatKey,
  publicKey: string,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    "spki",
    toArrayBuffer(fromBase64(publicKey)),
    rsaAlgorithm,
    false,
    ["encrypt"],
  );
  const rawKey = await crypto.subtle.exportKey("raw", entry.key);
  const wrapped = await crypto.subtle.encrypt(
    { name: "RSA-OAEP", label: encoder.encode(`sbu-chat-key:${conversationId}:${entry.keyId}`) },
    key,
    rawKey,
  );
  new Uint8Array(rawKey).fill(0);
  return toBase64(wrapped);
}

function parseEncryptedContent(content: string): { keyId: string; iv: Uint8Array; data: Uint8Array } | null {
  if (!isEncryptedChatContent(content)) return null;
  try {
    const decoded = JSON.parse(decoder.decode(fromBase64(content.slice("e2ee:v1:".length)))) as {
      keyId: string;
      iv: string;
      data: string;
    };
    if (!decoded.keyId || !decoded.iv || !decoded.data) return null;
    return { keyId: decoded.keyId, iv: fromBase64(decoded.iv), data: fromBase64(decoded.data) };
  } catch {
    return null;
  }
}

export async function encryptChatText(
  conversationId: string,
  entry: ConversationChatKey,
  content: string,
): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv,
      additionalData: encoder.encode(`sbu-chat-message:${conversationId}:${entry.keyId}`),
    },
    entry.key,
    encoder.encode(content),
  );
  return `e2ee:v1:${toBase64(encoder.encode(JSON.stringify({
    keyId: entry.keyId,
    iv: toBase64(iv),
    data: toBase64(data),
  })))}`;
}

export async function decryptChatText(
  userId: string,
  conversationId: string,
  content: string,
): Promise<EncryptedMessage> {
  const parsed = parseEncryptedContent(content);
  if (!parsed) {
    if (isEncryptedChatContent(content)) throw new Error("This encrypted chat message is damaged.");
    return { content, keyId: "" };
  }
  const key = (await getConversationKeys(userId, conversationId))
    .find((entry) => entry.keyId === parsed.keyId);
  if (!key) throw new Error("This device does not have the key for this message yet.");
  const clearText = await crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv: toArrayBuffer(parsed.iv),
      additionalData: encoder.encode(`sbu-chat-message:${conversationId}:${parsed.keyId}`),
    },
    key.key,
    toArrayBuffer(parsed.data),
  );
  return { content: decoder.decode(clearText), keyId: parsed.keyId };
}

export async function encryptChatAudio(
  conversationId: string,
  entry: ConversationChatKey,
  audio: Blob,
): Promise<Blob> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipherText = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv,
      additionalData: encoder.encode(`sbu-chat-audio:${conversationId}:${entry.keyId}`),
    },
    entry.key,
    await audio.arrayBuffer(),
  );
  const header = new Uint8Array(60);
  header.set(encoder.encode("SBU-E2EE-v1!"), 0);
  header.set(iv, 12);
  header.set(encoder.encode(entry.keyId), 24);
  return new Blob([header, cipherText], { type: "application/octet-stream" });
}

export async function decryptChatAudio(
  userId: string,
  conversationId: string,
  encrypted: Blob,
  mediaType: string,
): Promise<Blob> {
  const bytes = new Uint8Array(await encrypted.arrayBuffer());
  if (bytes.length < 76 || decoder.decode(bytes.subarray(0, 12)) !== "SBU-E2EE-v1!") {
    throw new Error("This voice message is not a valid encrypted audio payload.");
  }
  const keyId = decoder.decode(bytes.subarray(24, 60));
  const key = (await getConversationKeys(userId, conversationId))
    .find((entry) => entry.keyId === keyId);
  if (!key) throw new Error("This device does not have the voice message key yet.");
  const iv = bytes.subarray(12, 24);
  const clearAudio = await crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv,
      additionalData: encoder.encode(`sbu-chat-audio:${conversationId}:${keyId}`),
    },
    key.key,
    toArrayBuffer(bytes.subarray(60)),
  );
  return new Blob([clearAudio], { type: mediaType });
}

export function encryptedMessageKeyId(content: string): string {
  return parseEncryptedContent(content)?.keyId ?? "";
}
