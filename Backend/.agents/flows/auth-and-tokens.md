# جریان: احراز هویت و توکن‌ها

فایل‌ها: `features/auth/{models,schemas,service,router}.py`, `core/security.py`, `core/dependencies.py`.

## توکن‌ها
| | access token | refresh token |
|---|---|---|
| قالب | JWT، `HS256`، payload: `sub` (uuid کاربر)، `role`، `exp` | رشته‌ی مبهم `secrets.token_urlsafe(48)` (بدون claim) |
| عمر | `ACCESS_TOKEN_EXPIRE_MINUTES` = ۳۰ | `REFRESH_TOKEN_EXPIRE_DAYS` = ۳۰ |
| ذخیره‌ی سرور | ❌ (stateless) | فقط **SHA-256** آن در `refresh_tokens` |
| استفاده | هدر `Authorization: Bearer …` روی هر درخواست | فقط `POST /auth/refresh` و `/auth/logout` |
| ابطال | ممکن نیست تا انقضا (یا حذف کاربر) | `revoked_at` |

کلید امضا: `JWT_SECRET_KEY` (**باید در پروداکشن عوض شود**، پیش‌فرض `change-me-in-production`).
گذرواژه: bcrypt؛ طول ۸ تا ۷۲ نویسه (bcrypt بعد از ۷۲ بایت نادیده می‌گیرد/خطا می‌دهد، پس در schema محدود شده تا ۴۲۲ شود نه ۵۰۰). ایمیل با `EmailStr`.

## ثبت‌نام `POST /auth/register`
1. `pg_advisory_xact_lock(7_204_001)` — سریالی‌سازی ثبت‌نام‌ها.
2. ایمیل تکراری → 409.
3. اگر هیچ کاربری در جدول نیست → `role=super_admin`؛ وگرنه `user`.
4. commit، سپس `_issue_tokens` (access + refresh جدید) و پاسخ `TokenResponse{access_token, refresh_token, token_type, user}`.
⚠️ ثبت‌نام **عمومی و باز** است (هر کسی می‌تواند حساب `user` بسازد؛ تا عضو تیم/پروژه نشود به داده‌ای نمی‌رسد، **مگر ابزار مالی** که الان به نقش وابسته نیست). در پروداکشن باید با Caddy مسدود شود (`respond @register 403`، ← [../ops/infra-and-deploy.md](../ops/infra-and-deploy.md)). endpoint ساخت کاربر توسط ادمین وجود ندارد؛ بعد از بستن ثبت‌نام باید راهی برای ساخت کاربر فراهم شود (نیاز به تصمیم).

## ورود `POST /auth/login`
ایمیل را می‌یابد و `verify_password`؛ خطا → 401 «Invalid email or password» (پیام یکسان برای ایمیل نامعتبر و رمز غلط). هیچ rate limit/قفل حساب وجود ندارد.

## تمدید `POST /auth/refresh` (rotation اتمیک)
```
UPDATE refresh_tokens SET revoked_at=now
 WHERE token_hash=:h AND revoked_at IS NULL AND expires_at>now
RETURNING user_id
```
- اگر ردیفی برنگشت → rollback و 401 (توکن ناشناخته، منقضی، یا قبلاً استفاده‌شده).
- اتمیک بودن یعنی یک توکن هرگز دو بار قابل‌استفاده نیست (حتی هم‌زمان).
- سپس کاربر خوانده، commit، و جفت توکن جدید صادر می‌شود.
- استفاده‌ی دوباره از توکن چرخانده‌شده فقط 401 می‌دهد؛ **سایر توکن‌های کاربر ابطال نمی‌شوند** (تشخیص سرقت به‌صورت خودکار واکنش ندارد).

## خروج `POST /auth/logout` (204)
refresh token را باطل می‌کند (ناشناخته = بی‌صدا موفق). access token تا انقضا معتبر می‌ماند.

## پروفایل `GET /auth/me`
`UserRead{id,email,full_name,role,created_at}`.

## اعتبارسنجی هر درخواست (`get_current_user`)
decode JWT (خطا → 401) → `sub` → خواندن `User` از DB (نبود → 401). سپس `get_current_user_context` تیم/پروژه‌ها را می‌خواند. جزئیات: [../03-access-control.md](../03-access-control.md).

## WebSocket
مرورگر header نمی‌فرستد؛ توکن access در `?token=` می‌آید و `_authenticate_websocket` همان decode+خواندن کاربر را انجام می‌دهد. خطا → بستن اتصال با کد `1008`.

## تغییر نقش
`PATCH /admin/users/{id}/role` فقط super_admin. نقش بعدی درخواست بعدی اعمال می‌شود (چون از DB خوانده می‌شود). **هیچ API برای حذف/غیرفعال‌کردن کاربر، تغییر رمز، یا بازیابی رمز نیست.**
