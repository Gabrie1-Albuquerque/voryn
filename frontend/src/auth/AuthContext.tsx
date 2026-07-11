import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchCurrentUser, login as apiLogin, logout as apiLogout } from "../api/auth";
import type { CurrentUser } from "../api/types";
import { tokenStore } from "../lib/tokenStore";

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = tokenStore.onLoggedOut(() => setUser(null));

    if (tokenStore.getAccessToken()) {
      fetchCurrentUser()
        .then(setUser)
        .catch(() => tokenStore.clear())
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }

    return unsubscribe;
  }, []);

  async function login(email: string, password: string) {
    const tokens = await apiLogin(email, password);
    tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
    setUser(await fetchCurrentUser());
  }

  async function logout() {
    const refreshToken = tokenStore.getRefreshToken();
    tokenStore.clear();
    setUser(null);
    if (refreshToken) {
      // Best-effort: the user is logged out locally regardless of whether
      // this network call succeeds.
      apiLogout(refreshToken).catch(() => {});
    }
  }

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
