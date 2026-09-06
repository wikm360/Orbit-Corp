"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";

import { authApi } from "../api/authApi";
import { BrandPanel } from "../components/BrandPanel";
import { useAuthStore } from "../hooks/useAuthStore";
import { authErrorMessage } from "../lib/errorMessages";

type Mode = "login" | "register";

const COPY: Record<Mode, { title: string; subtitle: string; submit: string; switchText: string; switchAction: string }> = {
  login: {
    title: "سلام! خوش اومدی 👋",
    subtitle: "برای ادامه، وارد حساب سازمانی‌ات شو.",
    submit: "ورود",
    switchText: "هنوز حساب نداری؟",
    switchAction: "بساز",
  },
  register: {
    title: "بیا شروع کنیم ✨",
    subtitle: "با ایمیل سازمانی‌ات یک حساب بساز؛ کمتر از یک دقیقه طول می‌کشد.",
    submit: "ساخت حساب",
    switchText: "قبلاً ثبت‌نام کرده‌ای؟",
    switchAction: "وارد شو",
  },
};

export function LoginScreen() {
  const router = useRouter();
  const setSession = useAuthStore((state) => state.setSession);

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const copy = COPY[mode];

  function switchMode() {
    setMode(mode === "login" ? "register" : "login");
    setError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const response =
        mode === "login"
          ? await authApi.login({ email: email.trim(), password })
          : await authApi.register({
              email: email.trim(),
              password,
              full_name: fullName.trim() || undefined,
            });
      setSession(response.access_token, response.user);
      router.push("/chat");
    } catch (err) {
      setError(authErrorMessage(err, mode));
      setIsLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-gray-50 lg:grid-cols-[1.1fr_1fr]">
      <BrandPanel />

      <section className="flex flex-col items-center justify-center px-4 py-10 sm:px-8">
        {/* compact brand header for mobile / tablet, where the panel is hidden */}
        <div className="mb-8 flex items-center gap-3 lg:hidden">
          <Image
            src="/logo.jpg"
            alt="لوگوی شرکت محور گستر نصر"
            width={56}
            height={50}
            priority
            className="h-12 w-auto rounded-lg"
          />
          <div>
            <p className="font-bold text-brand-800">شرکت محور گستر نصر</p>
            <p className="text-xs text-gray-500">دستیار هوشمند سازمانی</p>
          </div>
        </div>

        <div
          key={mode}
          className="w-full max-w-md rounded-3xl border border-gray-100 bg-white p-8 shadow-card animate-fade-up sm:p-10"
        >
          <h1 className="text-2xl font-bold text-gray-900">{copy.title}</h1>
          <p className="mt-2 text-sm leading-relaxed text-gray-500">{copy.subtitle}</p>

          <form onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-5">
            {mode === "register" && (
              <Input
                label="نام و نام خانوادگی"
                autoComplete="name"
                placeholder="مثلاً: سارا محمدی"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                startIcon={<UserIcon />}
              />
            )}

            <Input
              label="ایمیل سازمانی"
              type="email"
              inputMode="email"
              autoComplete="email"
              required
              dir="ltr"
              placeholder="name@company.com"
              className="text-left placeholder:text-left"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              startIcon={<MailIcon />}
            />

            <Input
              label="رمز عبور"
              type={showPassword ? "text" : "password"}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={8}
              dir="ltr"
              placeholder="••••••••"
              className="text-left placeholder:text-left"
              hint={mode === "register" ? "حداقل ۸ کاراکتر" : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              startIcon={<LockIcon />}
              endSlot={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "پنهان کردن رمز" : "نمایش رمز"}
                  className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              }
            />

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border border-red-100 bg-red-50 px-3.5 py-3 text-sm text-red-700"
              >
                <AlertIcon />
                <span>{error}</span>
              </div>
            )}

            <Button type="submit" size="lg" isLoading={isLoading} className="mt-1 w-full">
              {isLoading ? "چند لحظه..." : copy.submit}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            {copy.switchText}{" "}
            <button
              type="button"
              onClick={switchMode}
              className="font-bold text-brand-600 underline-offset-4 hover:underline"
            >
              {copy.switchAction}
            </button>
          </p>
        </div>

        <p className="mt-8 text-center text-xs text-gray-400">
          مشکلی در ورود داری؟ با واحد فناوری اطلاعات تماس بگیر.
        </p>
      </section>
    </main>
  );
}

/* ---- tiny inline icons (no icon library dependency) ---- */

function iconProps(size = 18) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
}

function MailIcon() {
  return (
    <svg {...iconProps()}>
      <rect x="3" y="5" width="18" height="14" rx="2.5" />
      <path d="m4 7 8 6 8-6" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg {...iconProps()}>
      <rect x="5" y="11" width="14" height="10" rx="2.5" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg {...iconProps()}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M3 3l18 18" />
      <path d="M10.6 5.2A10.9 10.9 0 0 1 12 5c6.5 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.1" />
      <path d="M6.6 6.6C3.8 8.5 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.3-1" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg {...iconProps(18)} className="mt-0.5 shrink-0">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  );
}
