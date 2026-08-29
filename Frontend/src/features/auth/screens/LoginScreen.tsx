"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError } from "@/shared/lib/apiClient";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";

import { authApi } from "../api/authApi";
import { useAuthStore } from "../hooks/useAuthStore";

export function LoginScreen() {
  const router = useRouter();
  const setSession = useAuthStore((state) => state.setSession);

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const response =
        mode === "login"
          ? await authApi.login({ email, password })
          : await authApi.register({ email, password, full_name: fullName || undefined });
      setSession(response.access_token, response.user);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold text-gray-900">
          دستیار هوشمند سازمانی
        </h1>
        <p className="mb-6 text-sm text-gray-500">
          {mode === "login" ? "ورود به حساب کاربری" : "ساخت حساب کاربری جدید"}
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === "register" && (
            <Input
              label="نام کامل"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
          <Input
            label="ایمیل"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="رمز عبور"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <p className="text-sm text-red-600">{error}</p>}

          <Button type="submit" isLoading={isLoading} className="mt-2">
            {mode === "login" ? "ورود" : "ثبت‌نام"}
          </Button>
        </form>

        <button
          className="mt-4 text-sm text-brand-600 hover:underline"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "حساب کاربری ندارید؟ ثبت‌نام کنید" : "قبلاً ثبت‌نام کرده‌اید؟ وارد شوید"}
        </button>
      </div>
    </div>
  );
}
