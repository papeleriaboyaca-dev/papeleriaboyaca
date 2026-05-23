import { create } from "zustand";
import { persist } from "zustand/middleware";
import { parseJwt } from "@/lib/utils";
import type { AuthTokenPayload, UserRole } from "@/types";
import { useCartStore } from "@/store/cartStore";

interface AuthState {
  token: string | null;
  user: AuthTokenPayload | null;
  setToken: (token: string, refreshToken?: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  hasRole: (...roles: UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,

      setToken: (token, refreshToken) => {
        const payload = parseJwt(token) as AuthTokenPayload | null;
        sessionStorage.setItem("access_token", token);
        if (refreshToken) sessionStorage.setItem("refresh_token", refreshToken);
        set({ token, user: payload });
      },

      logout: () => {
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("refresh_token");
        useCartStore.getState().clear();
        set({ token: null, user: null });
      },

      isAuthenticated: () => {
        const { token, user } = get();
        if (!token || !user) return false;
        return user.exp * 1000 > Date.now();
      },

      hasRole: (...roles) => {
        const { user } = get();
        if (!user) return false;
        return roles.includes(user.user_role);
      },
    }),
    {
      name: "pb-auth",
      storage: {
        getItem: (key) => { const v = sessionStorage.getItem(key); return v ? JSON.parse(v) : null; },
        setItem: (key, value) => sessionStorage.setItem(key, JSON.stringify(value)),
        removeItem: (key) => sessionStorage.removeItem(key),
      },
      partialize: (state) => ({ token: state.token, user: state.user }) as AuthState,
    }
  )
);
