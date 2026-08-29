import { apiRequest } from "@/shared/lib/apiClient";
import { User } from "@/shared/types";

import { LoginPayload, RegisterPayload, TokenResponse } from "../types";

export const authApi = {
  login: (payload: LoginPayload) =>
    apiRequest<TokenResponse>("/auth/login", { method: "POST", body: payload }),

  register: (payload: RegisterPayload) =>
    apiRequest<TokenResponse>("/auth/register", { method: "POST", body: payload }),

  me: () => apiRequest<User>("/auth/me"),
};
