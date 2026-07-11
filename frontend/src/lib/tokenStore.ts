const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

type Listener = () => void;
const loggedOutListeners = new Set<Listener>();

export const tokenStore = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
  onLoggedOut(listener: Listener): () => void {
    loggedOutListeners.add(listener);
    return () => loggedOutListeners.delete(listener);
  },
  emitLoggedOut(): void {
    tokenStore.clear();
    for (const listener of loggedOutListeners) listener();
  },
};
