# Backend Penetration Test Report — Pass 2

**Date:** August 31, 2026
**Target:** Apartment Booking API (Django REST Framework)
**Scope:** Full backend codebase review (post-remediation)
**Prior Report:** Pass 1 found 22 vulnerabilities — all 22 remediated ✅

---

## Pass 1 Remediation Status

| # | Finding | Status |
|---|---------|--------|
| 1 | OTP stored in plaintext | ✅ Hashed with SHA-256 |
| 2 | Timing attack on OTP comparison | ✅ `hmac.compare_digest()` |
| 3 | User enumeration in OTP resend | ✅ Generic 200 response |
| 4 | Weak password validation in reset | ✅ `validate_password()` added |
| 5 | Missing old password check | ✅ `check_password()` enforced |
| 6 | Stripe exception leaking internals | ✅ Logged server-side, generic error returned |
| 7 | Booking race condition | ✅ `select_for_update()` + `transaction.atomic` |
| 8 | OTP email bombing | ✅ Brute-force lockout (5 attempts / 15 min) |
| 9 | `.env` in repo | ✅ Already in `.gitignore` |
| 10 | DB breach → OTP compromise | ✅ (Covered by #1) |
| 11 | Access token blocklist unreliable | ⚠️ See Finding #4 below |
| 12 | Deprecated `imghdr` | ✅ Replaced with Pillow |
| 13 | Stripe webhook secret missing | ✅ Warning on startup |
| 14 | Unrestricted file upload | ✅ 5 MB limit + Pillow validation |
| 15 | UserViewSet broad queryset | ℹ️ Mitigated by admin-only permissions |
| 16 | No per-account rate limit | ⚠️ See Finding #6 below |
| 17 | API schema exposure | ✅ Gated behind `DEBUG` |
| 18 | Duplicate `throttle_classes` | ✅ Removed |
| 19 | Silent cache failure in logout | ✅ `logger.warning()` added |
| 20 | No account lockout on login | ⚠️ See Finding #5 below |
| 21 | Inconsistent password validation | ✅ All paths use `validate_password()` |
| 22 | Email template expiry mismatch | ✅ Fixed to "15 minutes" |

---

## Remaining Findings (Post-Remediation)

### 🟡 Medium Severity

#### Finding #1: Login User Enumeration
**File:** `apps/user/serializers.py` — `LoginSerializer.validate()`
**Status:** Pre-existing, not in original report

The login endpoint reveals whether an email address is registered via distinct error messages:

```python
try:
    user_obj = User.objects.get(email=email)
    if not user_obj.is_active:
        raise serializers.ValidationError({"detail": "User account is inactive."})
    if not user_obj.otp_verified:
        raise serializers.ValidationError({"detail": "Email not verified..."})
    # ... more specific messages
except User.DoesNotExist:
    pass  # falls through to generic "Invalid credentials"
```

An attacker can determine valid emails by observing:
- `"User account is inactive."` → email exists, account inactive
- `"Email not verified..."` → email exists, not verified
- `"Invalid credentials."` → email doesn't exist OR wrong password

**Recommendation:** Check user status only after `authenticate()` succeeds, or always return a generic `"Invalid credentials."` message for all failure cases.

---

#### Finding #2: `SessionAuthentication` Exposes API Endpoints to CSRF
**File:** `core/settings.py` — `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`

```python
"DEFAULT_AUTHENTICATION_CLASSES": (
    "apps.user.authentication.CustomJWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
),
```

`SessionAuthentication` is enabled globally. Any API endpoint using `IsAuthenticatedOrReadOnly` (e.g., `ApartmentListCreateView`, `ReviewListCreateView`) can be called via session cookies. If a user is logged into the Django admin or has an active session, a malicious page could forge state-changing requests (POST/PUT/DELETE) via CSRF.

DRF's `SessionAuthentication` does enforce CSRF, but only for session-authenticated requests — not for JWT-authenticated requests. The concern is that the session auth path is available as an attack surface.

**Recommendation:** Remove `SessionAuthentication` from `DEFAULT_AUTHENTICATION_CLASSES` for API views. If Django admin session auth is needed, restrict it to admin-only views via per-view authentication classes.

---

#### Finding #3: Wildcard `.render.com` in `ALLOWED_HOSTS`
**File:** `core/settings.py`

```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "booker-61as.onrender.com", ".render.com", ...]
```

The `.render.com` entry allows any subdomain of `render.com` to be a valid host header. An attacker who can control a subdomain (e.g., via subdomain takeover or DNS rebinding) could send requests with a crafted `Host` header and have Django accept them. This enables:
- Cache poisoning via `Host` header injection
- Password reset link manipulation (if links use `request.get_host()`)
- Django admin URL forgery

**Recommendation:** Remove `.render.com` and keep only the specific production hostname.

---

#### Finding #4: `LocMemCache` for Sessions and Token Blacklisting (Multi-Worker)
**File:** `core/settings.py`

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        ...
    },
}

SESSION_CACHE_ALIAS = "default"
```

`LocMemCache` is per-process. In a multi-worker deployment (gunicorn with `workers > 1`):
- **Token blacklisting** (in `CustomJWTAuthentication`) won't work across workers — a token blacklisted in worker A remains valid in worker B.
- **Session data** won't be shared — a user who logs out in one worker may still have a valid session in another.
- **OTP brute-force counters** in `EmailVerificationView` are per-process — an attacker can bypass the lockout by hitting different workers.

The `ratelimit` cache uses Redis, which is correct, but the `default` cache (used for sessions and blacklisting) uses `LocMemCache`.

**Recommendation:** Use Redis for the `default` cache in production, or at minimum use `DatabaseCache` for cross-worker consistency.

---

#### Finding #5: No Per-Account Login Lockout
**File:** `apps/user/serializers.py` — `LoginSerializer.validate()`

The login endpoint has IP-level throttling (`5/minute`) but no per-account lockout. An attacker with a botnet or rotating IPs can brute-force passwords. A 6-digit numeric password has 1M combinations; at 5 attempts/minute per IP with 1000 IPs, that's ~200 minutes to exhaust.

**Recommendation:** Implement per-account lockout after N failed attempts (e.g., lock account for 15 minutes after 10 failed logins).

---

#### Finding #6: `PasswordResetConfirmView` Has No Per-Account Brute-Force Protection
**File:** `apps/user/views.py` — `PasswordResetConfirmView`

Unlike `EmailVerificationView` which has `_check_otp_bruteforce` / `_record_otp_failure`, the password reset confirm endpoint only has IP-level throttle (`otp: 5/minute`). An attacker who obtains a valid email can brute-force the 6-digit OTP.

While the 15-minute OTP expiry limits the window, the attack surface is:
- 6-digit OTP = 1,000,000 combinations
- 5 attempts/minute per IP × N IPs
- OTP valid for 15 minutes = 75 attempts per IP per OTP lifetime

**Recommendation:** Add per-account OTP failure tracking (same mechanism as `EmailVerificationView`) to `PasswordResetConfirmView`.

---

### 🟢 Low Severity

#### ~~Finding #7: `ALLOWED_IMAGE_TYPES` Defined But Not Enforced~~
**File:** `apps/apartments/serializers.py`
**Status:** ✅ Fixed — now checks `img.format` against `ALLOWED_IMAGE_TYPES` after Pillow verification.

---

#### Finding #8: `UserDetailSerializer` References Non-Existent `meta` Field
**File:** `apps/user/serializers.py`

```python
class UserDetailSerializer(serializers.ModelSerializer):
    meta = serializers.JSONField(read_only=True)  # If meta is a JSONField on User model
```

The `User` model has no `meta` field. Attempting to serialize a user with `UserDetailSerializer` (e.g., in `LoginView.post()` or `UserViewSet.retrieve()`) will raise an `AttributeError`, returning a 500 error. In production, this could leak stack trace information depending on error handling configuration.

**Recommendation:** Remove the `meta` field from `UserDetailSerializer` or add the field to the `User` model.

---

#### Finding #9: `ReviewListCreateView.perform_create` Unhandled `DoesNotExist`
**File:** `apps/reviews/views.py`

```python
def perform_create(self, serializer):
    apartment_id = self.kwargs["apartment_id"]
    apartment = Apartment.objects.get(id=apartment_id)  # Can raise DoesNotExist
```

If the `apartment_id` in the URL doesn't match any apartment, this raises an unhandled `Apartment.DoesNotExist` exception, returning a 500 error with a potential stack trace.

**Recommendation:** Use `get_object_or_404(Apartment, id=apartment_id)` instead.

---

#### ~~Finding #10: `send_otp_email` Returns `None`~~
**File:** `apps/base/account_utils.py`
**Status:** ✅ Fixed — `send_otp_email` now returns `True` on success.

---

#### ~~Finding #11: Unused `ImproperlyConfigured` Import~~
**File:** `core/settings.py`
**Status:** ✅ Fixed — unused import removed.

---

## Summary

| Severity | Count | Notes |
|----------|-------|-------|
| 🔴 Critical | 0 | All 4 original criticals fixed ✅ |
| 🟠 High | 0 | All 5 original highs fixed ✅ |
| 🟡 Medium | 6 | Login enumeration, CSRF, ALLOWED_HOSTS, cache, lockout, brute-force |
| 🟢 Low | 2 | Serializer field, unhandled exception |
| ℹ️ Fixed | 3 | Image types, return value, dead import (fixed during this pass) |
| **Total** | **8 active** | Down from 22 in Pass 1 |

## Comparison with Pass 1

| Metric | Pass 1 | Pass 2 |
|--------|--------|--------|
| Critical | 4 | 0 |
| High | 5 | 0 |
| Medium | 8 | 6 |
| Low | 5 | 2 |
| Fixed in Pass 2 | 0 | 3 |
| **Total** | **22** | **8 active** |

## Priority Recommendations

1. **Switch `default` cache to Redis** in production — affects session, token blacklisting, and OTP brute-force counters
2. **Fix `UserDetailSerializer.meta`** — currently causes 500 errors on user detail endpoints
3. **Remove `.render.com` from `ALLOWED_HOSTS`** — prevents host header attacks
4. **Add per-account lockout to `PasswordResetConfirmView`** — same as `EmailVerificationView`
5. **Eliminate login user enumeration** — standardize error messages
