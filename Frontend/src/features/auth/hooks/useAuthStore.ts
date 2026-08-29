import { create } from "zustand";
import { persist } from "zustand/middleware";

import { User } from "@/shared/types";

interface AuthState {
  token: string | null;
  user: User | null;
  /** True once zustand has finished reading persisted state from localStorage.
   * Route guards must wait for this before deciding to redirect to /login -
   * otherwise every refresh briefly sees token=null (the pre-hydration
   * initial state) and bounces an already-logged-in user out. */
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
  setSession: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),
      setSession: (token, user) => {
        localStorage.setItem("auth_token", token);
        set({ token, user });
      },
      logout: () => {
        localStorage.removeItem("auth_token");
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
