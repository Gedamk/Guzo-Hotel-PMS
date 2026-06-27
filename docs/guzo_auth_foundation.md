# Guzo PMS Authentication Foundation

Guzo PMS uses `pms_users` as the user source for hotel staff authentication.

## Local Default User

Local development seeds the existing PMS users with password hashes when auth starts.

Default local admin:

```txt
Email: admin@guzo.local
Password: admin123
Property: DRE001
```

Set a safer local/pilot password before use:

```txt
GUZO_DEFAULT_ADMIN_PASSWORD=change-this-password
GUZO_JWT_SECRET=change-this-secret
```

## Login Flow

Frontend login calls:

```http
POST /auth/login
```

The backend verifies the password hash, active status, role, and property access, then returns:

```txt
access_token
expires_at
user role/property context
```

The frontend stores the token in local storage for the current PMS session and sends:

```http
Authorization: Bearer <token>
```

The current user endpoint is:

```http
GET /auth/me
```

Logout is client token clearing:

```http
POST /auth/logout
```

## Creating Users

Create or manage users in `pms_users` with:

```txt
email
full_name
role_key
property_code
is_active
password_hash
created_at
updated_at
```

Use the app hashing helper when creating users from backend code:

```python
from guzo_backend.services.pms_auth_service import hash_password
```

## Development Fallback

The old `X-PMS-User-Email` header is now only a local development/test fallback.

Enable it explicitly with:

```txt
GUZO_AUTH_DEV_FALLBACK=true
VITE_DEV_AUTH_FALLBACK=true
```

Normal PMS use should rely on JWT authentication.
