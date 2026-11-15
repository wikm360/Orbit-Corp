import { create } from "zustand";
import { persist } from "zustand/middleware";

import { User } from "@/shared/types";
import { revokeSession } from "@/shared/lib/apiClient";

export interface ImpersonatorSession {
  token: string;
  refreshToken: string;
  user: User;
}

interface AuthState {
  token: string | null;
  user: User | null;
  originalSession: ImpersonatorSession | null;
  /** True once zustand has finished reading persisted state from localStorage.
   * Route guards must wait for this before deciding to redirect to /login -
   * otherwise every refresh briefly sees token=null (the pre-hydration
   * initial state) and bounces an already-logged-in user out. */
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
  setSession: (token: string, refreshToken: string, user: User) => void;
  startImpersonation: (token: string, refreshToken: string, user: User) => void;
  stopImpersonationSession: (token?: string, refreshToken?: string, user?: User) => void;
  /** Replaces the cached profile (e.g. after the server changed this user's permissions) without touching tokens. */
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      originalSession: null,
      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),
      setSession: (token, refreshToken, user) => {
        localStorage.setItem("auth_token", token);
        localStorage.setItem("refresh_token", refreshToken);
        set({ token, user });
      },
      startImpersonation: (token, refreshToken, user) => {
        const currentToken = get().token;
        const currentRefreshToken = (typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null) || "";
        const currentUser = get().user;
        const originalSession =
          get().originalSession ||
          (currentToken && currentUser
            ? {
                token: currentToken,
                refreshToken: currentRefreshToken,
                user: currentUser,
              }
            : null);

        if (typeof window !== "undefined") {
          localStorage.setItem("auth_token", token);
          localStorage.setItem("refresh_token", refreshToken);
        }
        set({ token, user, originalSession });
      },
      stopImpersonationSession: (token, refreshToken, user) => {
        const original = get().originalSession;
        const nextToken = token || original?.token || null;
        const nextRefreshToken = refreshToken || original?.refreshToken || "";
        const nextUser = user || original?.user || null;

        if (typeof window !== "undefined") {
          if (nextToken) {
            localStorage.setItem("auth_token", nextToken);
          } else {
            localStorage.removeItem("auth_token");
          }
          if (nextRefreshToken) {
            localStorage.setItem("refresh_token", nextRefreshToken);
          } else {
            localStorage.removeItem("refresh_token");
          }
        }

        set({
          token: nextToken,
          user: nextUser,
          originalSession: null,
        });
      },
      setUser: (user) => set({ user }),
      logout: () => {
        void revokeSession();
        if (typeof window !== "undefined") {
          localStorage.removeItem("auth_token");
          localStorage.removeItem("refresh_token");
        }
        set({ token: null, user: null, originalSession: null });
      },
    }),
    {
      name: "auth-store",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
