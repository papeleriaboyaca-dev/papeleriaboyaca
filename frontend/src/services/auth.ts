import { api } from "@/lib/axios";
import type { AuthResponse, LoginRequest, RegisterRequest, UserProfile } from "@/types";

export const authService = {
  login: (data: LoginRequest) =>
    api.post<AuthResponse>("/auth/login", data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    api.post<AuthResponse>("/auth/register", data).then((r) => r.data),

  me: () =>
    api.get<UserProfile>("/users/me").then((r) => r.data),

  updateMe: (data: { first_name?: string; last_name?: string; phone?: string; city?: string; document_id?: string }) =>
    api.put<UserProfile>("/users/me", data).then((r) => r.data),

  changePassword: (new_password: string) =>
    api.post("/auth/change-password", { new_password }).then((r) => r.data),

  forgotPassword: (email: string, redirect_url?: string) =>
    api.post("/auth/forgot-password", { email, redirect_url }).then((r) => r.data),
};
