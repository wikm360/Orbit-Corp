import { create } from "zustand";
import { persist } from "zustand/middleware";

import { User } from "@/shared/types";
import { revokeSession } from "@/shared/lib/apiClient";

interface AuthState {
  token: string | null;
  user: User | null;
  /** True once zustand has finished reading persisted state from localStorage.
   * Route guards must wait for this before deciding to redirect to /login -
   * otherwise every refresh briefly sees token=null (the pre-hydration
   * initial state) and bounces an already-logged-in user out. */
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
  setSession: (token: string, refreshToken: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),
      setSession: (token, refreshToken, user) => {
        localStorage.setItem("auth_token", token);
        localStorage.setItem("refresh_token", refreshToken);
        set({ token, user });
      },
      logout: () => {
        void revokeSession();
        localStorage.removeItem("auth_token");
        localStorage.removeItem("refresh_token");
        set({ token: null, user: null });
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
