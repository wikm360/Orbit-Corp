"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { adminApi } from "@/features/admin/api/adminApi";
import { User, UserRole } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

function getRoleLabel(role: UserRole): string {
  switch (role) {
    case "super_admin":
      return "مدیر ارشد";
    case "admin":
      return "مدیر";
    case "user":
      return "کاربر عادی";
    default:
      return role;
  }
}

function getRoleBadgeClass(role: UserRole): string {
  switch (role) {
    case "super_admin":
      return "bg-purple-100 text-purple-700 border-purple-200";
    case "admin":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "user":
      return "bg-slate-100 text-slate-700 border-slate-200";
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
}

export function UserSwitcherHeader() {
  const router = useRouter();
  const { user, originalSession, startImpersonation, stopImpersonationSession } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [switchingUserId, setSwitchingUserId] = useState<string | null>(null);
  const [isStopping, setIsStopping] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const isImpersonating = Boolean(originalSession || user?.is_impersonated);
  const isSuperAdmin = user?.role === "super_admin" || originalSession?.user?.role === "super_admin";

  const shouldRender = isSuperAdmin || isImpersonating;

  // Load all users on mount if shouldRender
  useEffect(() => {
    let ignore = false;
    if (shouldRender) {
      adminApi.listUsers()
        .then((data) => {
          if (!ignore) {
            setUsers(data);
            setLoadError(null);
          }
        })
        .catch(() => {
          if (!ignore) {
            setLoadError("خطا در دریافت لیست کاربران");
          }
        });
    }
    return () => {
      ignore = true;
    };
  }, [shouldRender]);

  // Manual refresh helper
  const refreshUsersList = async () => {
    setIsLoadingUsers(true);
    setLoadError(null);
    try {
      const data = await adminApi.listUsers();
      setUsers(data);
    } catch {
      setLoadError("خطا در دریافت لیست کاربران");
    } finally {
      setIsLoadingUsers(false);
    }
  };

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      const timer = setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
      return () => {
        clearTimeout(timer);
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Handle switching to target user
  const handleSwitchUser = async (targetUser: User) => {
    if (targetUser.id === user?.id) {
      setIsOpen(false);
      return;
    }
    try {
      setSwitchingUserId(targetUser.id);
      const res = await adminApi.impersonateUser(targetUser.id);
      startImpersonation(res.access_token, res.refresh_token, res.user);
      setIsOpen(false);
      router.push("/chat");
      router.refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "خطا در تغییر حساب کاربری");
      setSwitchingUserId(null);
    }
  };

  // Handle stopping impersonation
  const handleStopImpersonation = async () => {
    try {
      setIsStopping(true);
      const res = await adminApi.stopImpersonation().catch(() => null);
      if (res) {
        stopImpersonationSession(res.access_token, res.refresh_token, res.user);
      } else {
        stopImpersonationSession();
      }
      router.push("/admin");
      router.refresh();
    } catch {
      stopImpersonationSession();
      router.push("/admin");
      router.refresh();
    }
  };

  const filteredUsers = useMemo(() => {
    if (!searchQuery.trim()) return users;
    const query = searchQuery.trim().toLowerCase();
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(query) ||
        (u.full_name && u.full_name.toLowerCase().includes(query)) ||
        getRoleLabel(u.role).includes(query)
    );
  }, [users, searchQuery]);

  if (!shouldRender) {
    return null;
  }

  const impersonatorEmail =
    user?.impersonator_email ||
    originalSession?.user?.email ||
    "مدیر ارشد";

  return (
    <div
      className={cn(
        "relative z-30 shrink-0 border-b transition-colors",
        isImpersonating
          ? "border-amber-400/80 bg-gradient-to-r from-amber-500/15 via-amber-400/20 to-orange-500/15 text-amber-950 backdrop-blur-sm"
          : "border-slate-200/80 bg-white/95 text-slate-800 backdrop-blur-sm"
      )}
    >
      <div className="mx-auto flex flex-wrap items-center justify-between gap-3 px-4 py-2 sm:px-6">
        {/* Right Info Section */}
        <div className="flex min-w-0 items-center gap-2.5">
          {isImpersonating ? (
            <>
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-sm ring-2 ring-amber-500/30">
                <svg className="h-4 w-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="font-semibold text-amber-900">حالت سوییچ کاربر:</span>
                  <span className="truncate font-bold text-amber-950">
                    {user?.full_name || user?.email}
                  </span>
                  {user?.full_name && (
                    <span className="truncate text-[11px] text-amber-800/80" dir="ltr">
                      ({user.email})
                    </span>
                  )}
                  {user && (
                    <span
                      className={cn(
                        "rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                        getRoleBadgeClass(user.role)
                      )}
                    >
                      {getRoleLabel(user.role)}
                    </span>
                  )}
                </div>
                <p className="truncate text-[10px] text-amber-800">
                  شما با هویت این کاربر وارد شده‌اید · حساب مدیر اصلی:{" "}
                  <span className="font-medium" dir="ltr">
                    {impersonatorEmail}
                  </span>
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-teal-600/10 text-teal-700">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="font-semibold text-slate-700">سوییچ حساب (Super Admin):</span>
                <span className="hidden text-slate-500 sm:inline">
                  ورود مستقیم به حساب هر کاربر بدون رمز عبور
                </span>
              </div>
            </>
          )}
        </div>

        {/* Left Actions Section */}
        <div className="flex items-center gap-2" ref={dropdownRef}>
          {/* User Switcher Dropdown Button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setIsOpen((prev) => !prev);
                if (!isOpen && users.length === 0) {
                  void refreshUsersList();
                }
              }}
              className={cn(
                "flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-medium transition shadow-sm",
                isImpersonating
                  ? "border-amber-300 bg-white/90 text-amber-900 hover:bg-white hover:border-amber-400"
                  : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
              )}
              aria-expanded={isOpen}
              aria-haspopup="true"
            >
              <svg className="h-3.5 w-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <span>{isImpersonating ? "سوییچ به کاربر دیگر" : "انتخاب کاربر برای ورود..."}</span>
              <svg
                className={cn("h-3.5 w-3.5 text-slate-400 transition-transform", isOpen && "rotate-180")}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Dropdown Popover */}
            {isOpen && (
              <div
                className="absolute left-0 mt-2 w-80 max-w-[90vw] sm:w-96 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl ring-1 ring-black/5 z-50 text-right animate-in fade-in zoom-in-95 duration-100"
              >
                <div className="mb-2.5 flex items-center justify-between border-b border-slate-100 pb-2 px-1">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-xs text-slate-800">لیست کاربران سیستم</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
                      {users.length.toLocaleString("fa-IR")} کاربر
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void refreshUsersList()}
                    title="تازه‌سازی لیست"
                    className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  >
                    <svg
                      className={cn("h-3.5 w-3.5", isLoadingUsers && "animate-spin")}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                </div>

                {/* Search Input */}
                <div className="relative mb-2">
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400">
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="جستجوی نام، ایمیل یا نقش..."
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-1.5 pl-3 pr-8 text-xs text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      className="absolute inset-y-0 left-0 flex items-center pl-2.5 text-slate-400 hover:text-slate-600"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>

                {/* Users List */}
                <div className="max-h-72 overflow-y-auto space-y-1 pr-0.5">
                  {users.length === 0 && !loadError ? (
                    <div className="py-8 text-center text-xs text-slate-400">
                      <svg className="mx-auto h-5 w-5 animate-spin text-teal-600 mb-2" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                      </svg>
                      در حال دریافت لیست کاربران...
                    </div>
                  ) : loadError ? (
                    <div className="py-4 text-center text-xs text-red-500">
                      {loadError}
                    </div>
                  ) : filteredUsers.length === 0 ? (
                    <div className="py-6 text-center text-xs text-slate-400">
                      کاربری با این مشخصات یافت نشد.
                    </div>
                  ) : (
                    filteredUsers.map((u) => {
                      const isCurrent = u.id === user?.id;
                      const isTargetSwitching = switchingUserId === u.id;
                      const avatarLetter = (u.full_name || u.email).slice(0, 1).toUpperCase();

                      return (
                        <button
                          key={u.id}
                          type="button"
                          disabled={isCurrent || isTargetSwitching}
                          onClick={() => void handleSwitchUser(u)}
                          className={cn(
                            "flex w-full items-center justify-between gap-2 rounded-xl p-2 text-right transition text-xs",
                            isCurrent
                              ? "bg-teal-50/60 text-slate-500 cursor-default ring-1 ring-teal-300/40"
                              : "hover:bg-slate-100 text-slate-700 cursor-pointer"
                          )}
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <span
                              className={cn(
                                "grid h-7 w-7 shrink-0 place-items-center rounded-lg text-xs font-semibold",
                                isCurrent
                                  ? "bg-teal-600 text-white"
                                  : "bg-slate-200 text-slate-700"
                              )}
                            >
                              {avatarLetter}
                            </span>
                            <div className="min-w-0">
                              <p className="truncate font-medium text-slate-900">
                                {u.full_name || u.email}
                              </p>
                              {u.full_name && (
                                <p className="truncate text-[10px] text-slate-400" dir="ltr">
                                  {u.email}
                                </p>
                              )}
                            </div>
                          </div>

                          <div className="flex shrink-0 items-center gap-1.5">
                            <span
                              className={cn(
                                "rounded-md border px-1.5 py-0.5 text-[9px] font-medium",
                                getRoleBadgeClass(u.role)
                              )}
                            >
                              {getRoleLabel(u.role)}
                            </span>
                            {isCurrent && (
                              <span className="rounded-full bg-teal-100 px-1.5 py-0.5 text-[9px] font-medium text-teal-800">
                                شما
                              </span>
                            )}
                            {isTargetSwitching && (
                              <svg className="h-3.5 w-3.5 animate-spin text-teal-600" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                              </svg>
                            )}
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Stop Impersonation Button */}
          {isImpersonating && (
            <button
              type="button"
              onClick={() => void handleStopImpersonation()}
              disabled={isStopping}
              className="flex items-center gap-1.5 rounded-xl bg-amber-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50"
            >
              {isStopping ? (
                <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
              ) : (
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              )}
              <span>بازگشت به حساب مدیریت</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
