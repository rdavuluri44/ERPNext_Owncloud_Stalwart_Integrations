// Sign-in: authentik passkey in the system browser + ERPNext OAuth with PKCE S256.
// No client secret in the app (public client). Tokens live only in Keychain / Keystore.
// The server binds tokens to the authentik browser session (erpnext_drive_integrations/portal/mobile.py),
// so signing out on the web also ends the app's access.
import Constants from 'expo-constants';
import * as AuthSession from 'expo-auth-session';
import * as SecureStore from 'expo-secure-store';
import * as WebBrowser from 'expo-web-browser';
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';

WebBrowser.maybeCompleteAuthSession();

// Tenant values come from the private mobile/.env (see .env.example), never from Git.
export const APP_NAME = Constants.expoConfig?.name ?? 'ERP';
export const ERP_URL = process.env.EXPO_PUBLIC_ERP_URL || 'https://erp.example.com';
// Public OAuth client ID of this ERPNext's "OAuth Client" record (not a secret; empty = sign-in disabled).
export const CLIENT_ID = process.env.EXPO_PUBLIC_OAUTH_CLIENT_ID ?? '';
const OAUTH = `${ERP_URL}/api/method/frappe.integrations.oauth2`;
const discovery: AuthSession.DiscoveryDocument = {
  authorizationEndpoint: `${OAUTH}.authorize`,
  tokenEndpoint: `${OAUTH}.get_token`,
};
// Own build: <scheme>://oauth/callback. Expo Go: exp://<pc>:8081/--/oauth/callback, allowed only on the
// test site's OAuth client (P38: the app's client is blocked on production until release).
const scheme = Constants.expoConfig?.scheme;
export const REDIRECT_URI = AuthSession.makeRedirectUri({
  scheme: Array.isArray(scheme) ? scheme[0] : scheme,
  path: 'oauth/callback',
});

const TOKENS = 'erp.tokens';
const USER = 'erp.user';

export type User = { name: string; email: string; roles: string[] };
type Status = 'loading' | 'signedOut' | 'signedIn';
/** Why the app is signed out: the person pressed Sign out, or the server ended the sign-in (expired, revoked). */
export type Ended = 'signOut' | 'expired' | null;

/** The server refused our tokens (signed out on the web, user disabled, expired). Not a network error. */
export class SignedOutError extends Error {}

type Auth = {
  status: Status;
  ended: Ended;
  user: User | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  /** fetch() to ERPNext as the signed-in user. ERPNext applies that user's permissions. */
  api: (path: string, init?: RequestInit) => Promise<Response>;
};

const AuthContext = createContext<Auth | null>(null);

// This device only: a phone backup restored elsewhere does not carry the sign-in.
const LOCAL = { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY };

async function saveTokens(t: AuthSession.TokenResponse) {
  await SecureStore.setItemAsync(TOKENS, JSON.stringify(t.getRequestConfig()), LOCAL);
}

async function clearLocal() {
  await Promise.all([SecureStore.deleteItemAsync(TOKENS), SecureStore.deleteItemAsync(USER)]);
}

// One refresh at a time: two screens refreshing together must not both spend the same refresh token.
let refreshing: Promise<string> | null = null;

async function accessToken(): Promise<string> {
  const raw = await SecureStore.getItemAsync(TOKENS);
  if (!raw) throw new SignedOutError('Not signed in');
  const tokens = new AuthSession.TokenResponse(JSON.parse(raw) as AuthSession.TokenResponseConfig);
  if (!tokens.shouldRefresh()) return tokens.accessToken;
  if (!tokens.refreshToken) throw new SignedOutError('Session expired');
  refreshing ??= tokens
    .refreshAsync({ clientId: CLIENT_ID }, discovery)
    .then(async (fresh) => {
      await saveTokens(fresh);
      return fresh.accessToken;
    })
    .catch((e: unknown) => {
      // Server said no (revoked / expired grant) -> signed out. Network failure -> keep tokens (offline).
      throw e instanceof AuthSession.TokenError ? new SignedOutError('Session ended') : e;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

/**
 * `onUser` runs before the app opens for a person (sign-in, or app start with a saved sign-in): it makes sure the
 * phone's offline data is theirs (lib/offline-store `adoptOffline`). `keepUnowned` is true at app start.
 */
export function AuthProvider({
  children,
  onUser,
}: {
  children: ReactNode;
  onUser?: (email: string, keepUnowned: boolean) => Promise<void>;
}) {
  const [status, setStatus] = useState<Status>('loading');
  const [ended, setEnded] = useState<Ended>(null);
  const [user, setUser] = useState<User | null>(null);

  const endLocal = async (why: Exclude<Ended, null>) => {
    await clearLocal();
    setUser(null);
    setEnded(why);
    setStatus('signedOut');
  };

  const api = async (path: string, init?: RequestInit) => {
    let token: string;
    try {
      token = await accessToken();
    } catch (e) {
      if (e instanceof SignedOutError) await endLocal('expired');
      throw e;
    }
    const res = await fetch(ERP_URL + path, {
      ...init,
      headers: { Accept: 'application/json', ...init?.headers, Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) {
      await endLocal('expired');
      throw new SignedOutError('Signed out on the server');
    }
    return res;
  };

  const loadProfile = async () => {
    const res = await api('/api/method/frappe.integrations.oauth2.openid_profile');
    if (!res.ok) throw new Error(`ERPNext profile failed (${res.status})`);
    const p = (await res.json()) as { name?: string; email?: string; roles?: string[] };
    const u: User = { name: p.name || p.email || '', email: p.email ?? '', roles: p.roles ?? [] };
    await SecureStore.setItemAsync(USER, JSON.stringify(u), LOCAL);
    setUser(u);
    return u;
  };

  // App start: signed in if tokens exist (works offline with the cached profile), then refresh the profile.
  useEffect(() => {
    (async () => {
      const [tokens, cached] = await Promise.all([
        SecureStore.getItemAsync(TOKENS),
        SecureStore.getItemAsync(USER),
      ]);
      if (!tokens) return setStatus('signedOut');
      if (cached) {
        const u = JSON.parse(cached) as User;
        await onUser?.(u.email, true).catch(() => {});
        setUser(u);
        setStatus('signedIn');
        loadProfile().catch(() => {}); // offline: keep the cached profile; SignedOutError already signed out
        return;
      }
      try {
        const u = await loadProfile();
        await onUser?.(u.email, true);
        setStatus('signedIn');
      } catch {
        await endLocal('expired');
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = async () => {
    if (!CLIENT_ID) throw new Error('Sign-in is not set up yet (no OAuth client ID in this build).');
    const request = new AuthSession.AuthRequest({
      clientId: CLIENT_ID,
      redirectUri: REDIRECT_URI,
      scopes: ['all', 'openid'],
      usePKCE: true, // S256 by default; the server refuses anything else
    });
    const result = await request.promptAsync(discovery);
    if (result.type === 'cancel' || result.type === 'dismiss') return;
    if (result.type !== 'success') {
      throw new Error(result.type === 'error' ? (result.error?.message ?? 'Sign-in failed') : 'Sign-in failed');
    }
    const tokens = await AuthSession.exchangeCodeAsync(
      {
        clientId: CLIENT_ID,
        code: result.params.code,
        redirectUri: REDIRECT_URI,
        extraParams: { code_verifier: request.codeVerifier ?? '' },
      },
      discovery,
    );
    await saveTokens(tokens);
    try {
      // The offline data must be this person's before any screen can send it (adoptOffline).
      const u = await loadProfile();
      await onUser?.(u.email, false);
    } catch (e) {
      await clearLocal();
      throw e;
    }
    setEnded(null);
    setStatus('signedIn');
  };

  const signOut = async () => {
    // Revoke on the server first (Bearer header is required by the gateway). Offline: the token still
    // dies when it expires or when the web session ends.
    try {
      const token = await accessToken();
      await fetch(`${OAUTH}.revoke_token`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `token=${encodeURIComponent(token)}&client_id=${encodeURIComponent(CLIENT_ID)}`,
      });
    } catch {
      // ignore: local sign-out must always succeed
    }
    await endLocal('signOut');
  };

  return (
    <AuthContext.Provider value={{ status, ended, user, signIn, signOut, api }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth must be used inside AuthProvider');
  return auth;
}

/** The latest `api`, for effects and event handlers that must not re-run each time the session renders. */
export function useApiRef() {
  const { api } = useAuth();
  const ref = useRef(api);
  useEffect(() => {
    ref.current = api;
  });
  return ref;
}
