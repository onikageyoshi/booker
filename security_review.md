# Security Review

Audit of the Booker Django/Django REST Framework backend.

Severity legend: **Critical** / **High** / **Medium** / **Low** / **Info**.

---

## Critical

### 1. JWT refresh-token blacklist is the only logout mechanism

`LogoutView` (apps/user/views.py:163) blacklists a single refresh token, but:
- The **access token** (1-day lifetime) remains valid until expiry.
- There is no token identifier allowlist/blocklist, so a stolen access token can be used for up to 24 h.
- A new refresh token is never issued on logout for the existing session.

**Impact:** Stolen access tokens cannot be revoked. Logout only prevents new token issuance.
**Fix:** Shorten access token lifetime (5–15 min) and add a token identifier (jti) allowlist checked by a custom `JWTAuthentication`. Alternatively, switch to opaque session/refresh tokens with server-side revocation.

### 2. Passwords validated only in serializers — not in model

`UserCreateSerializer` enforces 8-char + match, and `ChangePasswordSerializer` enforces 8-char + alnum, but none of Django's `AUTH_PASSWORD_VALIDATORS` (configured in settings.py:100) are run because the serializers use `.save()` / `create_user` directly without calling `django.contrib.auth.password_validation.validate_password`. `MinimumLengthValidator` etc. are therefore silently bypassed.
**Fix:** Run validators in the serializer `validate()` via `django.contrib.auth.password_validation.validate_password`.

### 3. Email verification is optional for login

In `LoginSerializer.validate` (apps/user/serializers.py:110), `authenticate()` succeeds as long as `is_active=True`. Account creation sets `is_active=False` and sends an OTP, but the email-verification step is not enforced in the authentication flow. A user who never clicks verification can still log in if another path sets `is_active=True`. More importantly, there is no guard preventing login *before* `otp_verified=True`.
**Fix:** Add an explicit `is_active` + `otp_verified` gate, or use a `is_verified` flag that must be true before login.

---

## High

### 4. Stripe webhook is CSRF-exempt and signature-checked only if secret present

`stripe_webhook` (apps/bookings/views.py:138) is decorated `@csrf_exempt` — expected for webhooks. The signature is verified with `stripe.Webhook.construct_event`, **but**:
- If `settings.STRIPE_WEBHOOK_SECRET` is empty/None (common in `.env` misconfiguration), `construct_event` raises and the view returns 400 — so the fail-closed behavior is correct, but there is no test asserting this.
- No replay-protection / idempotency beyond Stripe's own timestamp check (Stripe enforces 5-min window by default, so this is acceptable).
- The handler only acts on `checkout.session.completed`; all other events are silently ignored.

**Status:** Acceptable, but add an explicit assertion that `STRIPE_WEBHOOK_SECRET` is set at startup.

### 5. Booking ownership checks are object-level, but the **create** path trusts the URL

`ApartmentBookingListCreateView.post` (apps/bookings/views.py:48) verifies `request.user.is_authenticated`, but the guest is set from `self.request.user` in `perform_create`. This is fine, but note that a non-admin user can POST to any apartment's booking URL. There is no explicit host-guest separation or verification that the booking is being made by a genuine guest vs. the host booking their own property. Low practical risk but worth a domain rule.

### 6. No throttling on auth-sensitive endpoints individually

Global throttling (settings.py:133) is `AnonRateThrottle: 10/min` and `UserRateThrottle: 1000/day`.
- The OTP endpoints (`verify/email`, `password-reset/request`) are **not** individually throttled, and there is a declared `otp: 5/minute` rate that is never referenced by any view. An attacker can spam OTP requests to any email.
- Login has no per-account lockout / exponential backoff.

**Fix:** Add `throttle_scope = "otp"` (or a dedicated throttle) to OTP endpoints and a throttle on `LoginView`.

### 7. Host check uses direct object comparison

`ApartmentDetailView.put`/`delete` and `ReviewDetailView.put`/`delete` compare `obj.host / obj.user != request.user`. This is correct, but relies on the default `User` model being the only auth source. No impersonation protection exists (an admin could edit any apartment). Acceptable for this stage.

### 8. Password reset reveals nothing by design — but OTP verification does not expire server-side

`verfiy_user_otp` (apps/base/account_utils.py:133) enforces a 15-minute expiry, but the `EmailVerificationView.post` and `PasswordResetConfirmView` both call serializers that look up the OTP. The OTP expiry check lives in `verfiy_user_otp`, which is only used by `complete_password_reset`. The **email verification** path (`OTPVerificationSerializer.validate`) compares OTPs directly (apps/user/serializers.py:172) **without** checking `otp_created_at`. OTPs for email verification therefore never expire.
**Fix:** Add expiry check in `OTPVerificationSerializer.validate`.

---

## Medium

### 9. `CORS_ALLOW_ALL_ORIGINS = True` (settings.py:122)

Allows any origin to make credentialed requests. Combined with JWT in a cookie-less setup this is less severe, but it removes a layer of CSRF-style protection for any future cookie-based auth and allows any site to call the API.
**Fix:** Replace with an explicit `CORS_ALLOWED_ORIGINS` list.

### 10. `DEBUG = True` (settings.py:14)

The repo always runs with debug on unless overridden. In production this leaks environment variables, file paths, and stack traces.
**Fix:** Gate on `DEBUG = os.getenv("DEBUG", "false").lower() == "true"`.

### 11. Secret key fallback

`SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-secret-key-for-dev")` (settings.py:13). If `.env` is missing the project runs with a known-secret-key, allowing trivial session/key forgery.
**Fix:** Fail fast: `SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]` (no default) in production.

### 12. Email backend uses SMTP with TLS, credentials in env — fine, but `EMAIL_USE_TLS=True` and `EMAIL_USE_SSL=False` is contradictory if ever switched; not a vulnerability currently.

### 13. No `SECURITY_HEADERS` middleware

No `Content-Security-Policy`, `X-Frame-Options`, or `X-Content-Type-Options` hardening for any HTML (admin). Django admin is served at `/admin/`. For an API-only backend this is low priority.
**Fix:** Add `django.middleware.security.SecurityMiddleware` (already first in list) which sets some headers; consider `csp` headers if serving any HTML.

### 14. File / image uploads

Apartments accept a Cloudinary image (`CloudinaryField`). The serializer validates `content_type` starts with `image/`, which is a weak check (spoofable). Cloudinary itself strips most attack surfaces, so this is low risk. Consider server-side MIME validation.

### 15. Search/filtration

Only `DjangoFilterBackend` is enabled globally and no `SearchFilter`/`OrderingFilter` is wired for apartments. Not a vulnerability — just limited functionality.

---

## Low / Info

### 16. UUID primary keys leakable

Bookings use `UUIDField`; users use the `BaseModel` UUID PK. Enumeration is harder but not impossible if a UUID is predictable (default `uuid4` is fine).

### 17. `django-ratelimit` is installed and `RATELIMIT_ENABLE = True`, but **no view uses `@ratelimit`**

Settings configure it but no decorator applies it. No impact yet — just unused configuration.

### 18. `django-rest-passwordreset` and `django-filter` installed but password-reset uses custom flows

`django-rest-passwordreset` is in requirements but the code implements its own OTP flow via `account_utils`. Minor — no security impact.

### 19. `sslserver` in INSTALLED_APPS (settings.py:40)

Enables `runserver_plus`-style SSL. Not a vulnerability.

### 20. Hardcoded redirect URLs in Stripe checkout

`success_url`/`cancel_url` use `request.build_absolute_uri(f'/bookings/success/')` and `f'/bookings/{booking.id}/'` which are not valid API routes. This will cause the browser to land on a 404 after payment. This is a functional bug more than a security issue, but it indirectly affects the user-experience of a paid transaction flow.

### 21. `Booking.save()` recomputes total_price on every save when empty

`apps/bookings/models.py:46` — if `total_price` is falsy it recomputes. Since the serializer sets it explicitly, this is mostly defensive. Not exploitable for price manipulation on update because the serializer strips `status`/`payment_status`/`total_price` from updates, but note `update()` (serializer line 117) does **not** recompute `total_price` if `check_in`/`check_out` change. This could let a guest change dates without a price recalculation via the serializer path (though the model `save` would not recompute because `total_price` is already set). Low risk.

---

## Recommendations (priority)

1. **[High]** Add explicit per-endpoint throttling to OTP + login endpoints.
2. **[High]** Fix email-verification OTP — no expiry is enforced in that path.
3. **[Critical]** Address JWT revocation: shorten access lifetime, consider jti allowlist.
4. **[Critical]** Run `AUTH_PASSWORD_VALIDATORS` in serializers, or replace serializer-level rules.
5. **[Medium]** Set `DEBUG` from env and remove the unsafe `SECRET_KEY` default.
6. **[Medium]** Replace `CORS_ALLOW_ALL_ORIGINS` with an allowlist.
7. **[Medium]** Assert `STRIPE_WEBHOOK_SECRET` is configured at startup.
8. **[Low]** Validate uploaded image MIME type with a library (e.g. `python-magic`), not just `content_type`.
9. **[Info]** Fix Stripe `success_url` / `cancel_url` routing (functional).
