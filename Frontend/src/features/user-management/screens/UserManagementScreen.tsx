"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { workspaceApi } from "@/shared/lib/workspaceApi";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { ManagedUser, UserRole } from "@/shared/types";

const ROLE_LABEL: Record<UserRole, string> = { super_admin: "مدیر ارشد", admin: "مدیر", user: "کاربر" };
const EMPTY_FORM = { email: "", full_name: "", password: "" };

export function UserManagementScreen() {
  const currentUser = useAuthStore((state) => state.user);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState<{ id: string; email: string; full_name: string } | null>(null);
  const [resetting, setResetting] = useState<{ id: string; password: string } | null>(null);
  const [search, setSearch] = useState("");

  const refresh = useCallback(async () => {
    try {
      setUsers(await workspaceApi.managedUsers());
      setError(null);
    } catch (err) {
      setError(friendlyErrorMessage(err, "دریافت فهرست کاربران ناموفق بود."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  async function run(action: () => Promise<unknown>, success: string, failure: string): Promise<boolean> {
    setIsBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
      setNotice(success);
      return true;
    } catch (err) {
      setError(friendlyErrorMessage(err, failure));
      return false;
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    const ok = await run(() => workspaceApi.createManagedUser({ email: form.email.trim(), full_name: form.full_name.trim(), password: form.password }), "کاربر ایجاد شد.", "ایجاد کاربر ناموفق بود.");
    if (ok) setForm(EMPTY_FORM);
  }

  async function handleSaveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    const ok = await run(() => workspaceApi.updateManagedUser(editing.id, { email: editing.email.trim(), full_name: editing.full_name.trim() }), "اطلاعات کاربر ذخیره شد.", "ذخیره‌ی اطلاعات ناموفق بود.");
    if (ok) setEditing(null);
  }

  async function handleReset(event: FormEvent) {
    event.preventDefault();
    if (!resetting) return;
    const ok = await run(() => workspaceApi.resetManagedUserPassword(resetting.id, resetting.password), "رمز عبور تغییر کرد و نشست‌های قبلی کاربر بسته شد.", "تغییر رمز ناموفق بود.");
    if (ok) setResetting(null);
  }

  async function handleDelete(user: ManagedUser) {
    if (!window.confirm(`کاربر «${user.full_name || user.email}» برای همیشه حذف شود؟ چت‌های شخصی و عضویت‌های او نیز پاک می‌شود.`)) return;
    await run(() => workspaceApi.deleteManagedUser(user.id), "کاربر حذف شد.", "حذف کاربر ناموفق بود.");
  }

  if (isLoading) return <main className="mx-auto max-w-4xl p-6 text-sm text-gray-500">در حال بارگذاری...</main>;

  const query = search.trim().toLowerCase();
  const visible = users.filter((u) => !query || u.email.toLowerCase().includes(query) || (u.full_name ?? "").toLowerCase().includes(query));
  const createValid = form.email.trim() && form.full_name.trim() && form.password.length >= 8;

  return <main className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6 lg:p-8">
    <div>
      <h1 className="text-2xl font-bold text-gray-900">مدیریت کاربران</h1>
      <p className="mt-1 text-sm text-gray-500">ایجاد کاربر، تغییر ایمیل، ریست رمز عبور و حذف حساب‌های کاربران عادی</p>
    </div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded-xl bg-green-50 p-3 text-sm text-green-700">{notice}</p>}

    <section className="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 className="mb-4 font-semibold text-gray-800">کاربر جدید</h2>
      <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-3">
        <Input aria-label="نام کامل" placeholder="نام کامل" maxLength={255} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <Input aria-label="ایمیل" type="email" dir="ltr" placeholder="ایمیل" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input aria-label="رمز عبور" type="password" dir="ltr" autoComplete="new-password" placeholder="رمز عبور (حداقل ۸ نویسه)" maxLength={72} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <div className="sm:col-span-3"><Button type="submit" isLoading={isBusy} disabled={!createValid}>ایجاد کاربر</Button></div>
      </form>
    </section>

    <section className="rounded-2xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold text-gray-800">کاربران ({users.length})</h2>
        <Input aria-label="جست‌وجوی کاربر" placeholder="جست‌وجو بر اساس نام یا ایمیل" value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
      </div>
      <div className="space-y-3">{visible.map((user) => <div key={user.id} className="border-b border-gray-100 pb-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="break-all font-medium text-gray-900">{user.full_name || "—"}</span>
            <span dir="ltr" className="break-all text-gray-500">{user.email}</span>
            <Badge tone={user.role === "user" ? "gray" : "green"}>{ROLE_LABEL[user.role]}</Badge>
            {user.id === currentUser?.id && <Badge tone="gray">شما</Badge>}
          </span>
          <span className="flex flex-wrap items-center gap-2">
            {(user.manageable || user.id === currentUser?.id) && <>
              <Button type="button" variant="ghost" size="sm" disabled={isBusy} onClick={() => { setResetting(null); setEditing({ id: user.id, email: user.email, full_name: user.full_name ?? "" }); }}>ویرایش</Button>
              <Button type="button" variant="ghost" size="sm" disabled={isBusy} onClick={() => { setEditing(null); setResetting({ id: user.id, password: "" }); }}>ریست رمز</Button>
            </>}
            {user.manageable && <Button type="button" variant="danger" size="sm" disabled={isBusy} onClick={() => void handleDelete(user)}>حذف</Button>}
            {!user.manageable && user.id !== currentUser?.id && <span className="text-xs text-gray-400">خارج از دسترسی شما</span>}
          </span>
        </div>
        {editing?.id === user.id && <form onSubmit={handleSaveEdit} className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto_auto]">
          <Input aria-label="نام کامل" value={editing.full_name} maxLength={255} onChange={(e) => setEditing({ ...editing, full_name: e.target.value })} />
          <Input aria-label="ایمیل" type="email" dir="ltr" value={editing.email} onChange={(e) => setEditing({ ...editing, email: e.target.value })} />
          <Button type="submit" isLoading={isBusy} disabled={!editing.email.trim() || !editing.full_name.trim()}>ذخیره</Button>
          <Button type="button" variant="ghost" onClick={() => setEditing(null)}>انصراف</Button>
        </form>}
        {resetting?.id === user.id && <form onSubmit={handleReset} className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
          <Input aria-label="رمز عبور جدید" type="password" dir="ltr" autoComplete="new-password" placeholder="رمز جدید (حداقل ۸ نویسه)" maxLength={72} value={resetting.password} onChange={(e) => setResetting({ ...resetting, password: e.target.value })} />
          <Button type="submit" isLoading={isBusy} disabled={resetting.password.length < 8}>تغییر رمز</Button>
          <Button type="button" variant="ghost" onClick={() => setResetting(null)}>انصراف</Button>
        </form>}
      </div>)}
      {visible.length === 0 && <p className="text-sm text-gray-500">کاربری یافت نشد.</p>}</div>
    </section>
  </main>;
}
