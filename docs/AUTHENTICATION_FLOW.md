# Authentication Flow Documentation

Comprehensive documentation for the Unified Trading Intelligence Platform authentication system.

## Table of Contents

1. [Overview](#overview)
2. [Authentication Methods](#authentication-methods)
3. [Registration Flow](#registration-flow)
4. [Login Flow](#login-flow)
5. [Email Verification](#email-verification)
6. [Password Reset](#password-reset)
7. [Token Management](#token-management)
8. [Two-Factor Authentication](#two-factor-authentication)
9. [OAuth Integration](#oauth-integration)
10. [Rate Limiting](#rate-limiting)
11. [Security Best Practices](#security-best-practices)
12. [API Reference](#api-reference)

---

## Overview

The platform uses a comprehensive authentication system with multiple security layers:

- **JWT tokens** for stateless authentication
- **Email/password** authentication with strong password requirements
- **Email verification** for account security
- **Password reset** with secure token-based flow
- **Two-factor authentication (2FA)** for enhanced security
- **OAuth integration** with Google and GitHub
- **Rate limiting** to prevent abuse
- **Token refresh** for seamless user experience

### Technology Stack

- **FastAPI** - Web framework
- **Supabase Auth** - Authentication backend
- **JWT** - Token-based authentication
- **bcrypt** - Password hashing
- **pyotp** - 2FA implementation
- **slowapi** - Rate limiting

---

## Authentication Methods

### 1. Email/Password

Traditional authentication with email and password.

**Requirements**:
- Valid email address
- Strong password (min 8 chars, uppercase, lowercase, digit, special char)

**Endpoints**:
- `POST /auth/register` - Register new account
- `POST /auth/login` - Login with credentials

### 2. OAuth

Social authentication with third-party providers.

**Supported Providers**:
- Google
- GitHub

**Endpoints**:
- `GET /auth/oauth/google` - Initiate Google OAuth
- `GET /auth/oauth/github` - Initiate GitHub OAuth
- `GET /auth/oauth/callback/google` - Google OAuth callback
- `GET /auth/oauth/callback/github` - GitHub OAuth callback

### 3. Two-Factor Authentication (2FA)

Optional additional security layer using TOTP (Time-based One-Time Password).

**Endpoints**:
- `POST /auth/2fa/setup` - Setup 2FA
- `POST /auth/2fa/enable` - Enable 2FA
- `POST /auth/2fa/verify` - Verify 2FA code
- `POST /auth/2fa/disable` - Disable 2FA

---

## Registration Flow

### Step 1: User Registration

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "timezone": "America/New_York"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com"
}
```

### Step 2: Email Verification

User receives verification email with token.

```http
POST /auth/verify-email
Content-Type: application/json

{
  "token": "verification-token-from-email"
}
```

**Response**:
```json
{
  "message": "Email verified successfully"
}
```

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*(),.?":{}|<>)

### Rate Limiting

- **5 registrations per hour** per IP address

---

## Login Flow

### Step 1: User Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "remember_me": false
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com"
}
```

### Step 2: 2FA Verification (if enabled)

If user has 2FA enabled, verify the code:

```http
POST /auth/2fa/verify
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "code": "123456"
}
```

**Response**:
```json
{
  "message": "2FA code verified"
}
```

### Rate Limiting

- **10 login attempts per minute** per IP address

---

## Email Verification

### Verify Email

```http
POST /auth/verify-email
Content-Type: application/json

{
  "token": "verification-token-from-email"
}
```

### Resend Verification Email

```http
POST /auth/resend-verification
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Rate Limiting**:
- **3 resend requests per hour** per IP address

---

## Password Reset

### Step 1: Request Password Reset

```http
POST /auth/password-reset
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response**:
```json
{
  "message": "Password reset email sent if account exists"
}
```

**Note**: Always returns success to prevent email enumeration.

### Step 2: Confirm Password Reset

User receives reset email with token.

```http
POST /auth/password-reset/confirm
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass123!"
}
```

**Response**:
```json
{
  "message": "Password reset successfully"
}
```

### Change Password (Authenticated)

```http
POST /auth/change-password
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "current_password": "OldPass123!",
  "new_password": "NewSecurePass123!"
}
```

**Rate Limiting**:
- **3 reset requests per hour** per IP address
- **5 confirm requests per hour** per IP address

---

## Token Management

### Token Types

1. **Access Token**
   - Short-lived (24 hours default)
   - Used for API authentication
   - Included in Authorization header

2. **Refresh Token**
   - Long-lived (30 days default)
   - Used to obtain new access tokens
   - Stored securely by client

### Token Structure

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "type": "access",
  "iat": 1234567890,
  "exp": 1234654290
}
```

### Refresh Tokens

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com"
}
```

### Using Tokens

Include access token in Authorization header:

```http
GET /api/protected-endpoint
Authorization: Bearer {access_token}
```

### Token Expiration

- **Access Token**: 24 hours (configurable via `JWT_EXPIRATION_HOURS`)
- **Refresh Token**: 30 days (configurable via `JWT_REFRESH_EXPIRATION_DAYS`)

### Logout

```http
POST /auth/logout
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "message": "Logged out successfully"
}
```

**Rate Limiting**:
- **20 refresh requests per hour** per IP address

---

## Two-Factor Authentication

### Step 1: Setup 2FA

```http
POST /auth/2fa/setup
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344",
    "44332211",
    "55667788",
    "88776655",
    "99887766",
    "66778899",
    "33445566",
    "66554433"
  ]
}
```

### Step 2: Enable 2FA

Scan QR code with authenticator app (Google Authenticator, Authy, etc.) and verify:

```http
POST /auth/2fa/enable
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "code": "123456"
}
```

**Response**:
```json
{
  "message": "2FA enabled successfully"
}
```

### Step 3: Verify 2FA Code

During login or sensitive operations:

```http
POST /auth/2fa/verify
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "code": "123456"
}
```

**Response**:
```json
{
  "message": "2FA code verified"
}
```

### Disable 2FA

```http
POST /auth/2fa/disable
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "password": "SecurePass123!"
}
```

**Response**:
```json
{
  "message": "2FA disabled successfully"
}
```

### Backup Codes

- **10 backup codes** generated during setup
- Each code can be used once
- Store securely offline
- Use if authenticator app is unavailable

---

## OAuth Integration

### Google OAuth

#### Step 1: Initiate OAuth Flow

```http
GET /auth/oauth/google
```

Redirects to Google OAuth consent screen.

#### Step 2: Handle Callback

After user grants permission, Google redirects to:

```http
GET /auth/oauth/callback/google?code={auth_code}&state={state}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@gmail.com"
}
```

### GitHub OAuth

#### Step 1: Initiate OAuth Flow

```http
GET /auth/oauth/github
```

Redirects to GitHub OAuth consent screen.

#### Step 2: Handle Callback

After user grants permission, GitHub redirects to:

```http
GET /auth/oauth/callback/github?code={auth_code}&state={state}
```

**Response**: Same as Google OAuth

### OAuth Configuration

Set environment variables:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/oauth/callback/google

# GitHub OAuth
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_REDIRECT_URI=https://your-domain.com/auth/oauth/callback/github
```

---

## Rate Limiting

Rate limits are enforced per IP address to prevent abuse:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/register` | 5 requests | 1 hour |
| `/auth/login` | 10 requests | 1 minute |
| `/auth/refresh` | 20 requests | 1 hour |
| `/auth/verify-email` | 10 requests | 1 hour |
| `/auth/resend-verification` | 3 requests | 1 hour |
| `/auth/password-reset` | 3 requests | 1 hour |
| `/auth/password-reset/confirm` | 5 requests | 1 hour |

### Rate Limit Response

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "detail": "Rate limit exceeded. Try again in 3600 seconds."
}
```

---

## Security Best Practices

### For Developers

1. **Never log passwords or tokens**
2. **Use HTTPS in production**
3. **Rotate JWT secret regularly**
4. **Implement CSRF protection**
5. **Validate all input**
6. **Use secure password hashing (bcrypt)**
7. **Implement account lockout after failed attempts**
8. **Monitor for suspicious activity**

### For Users

1. **Use strong, unique passwords**
2. **Enable two-factor authentication**
3. **Don't share credentials**
4. **Use password manager**
5. **Verify email addresses**
6. **Keep backup codes secure**
7. **Logout from shared devices**
8. **Monitor account activity**

### Password Security

- **Hashing**: bcrypt with salt
- **Minimum length**: 8 characters
- **Complexity**: Uppercase, lowercase, digit, special char
- **No common passwords**: Checked against common password list
- **No personal information**: Name, email, etc.

### Token Security

- **JWT secret**: Strong random string (min 32 chars)
- **Token expiration**: Short-lived access tokens
- **Refresh tokens**: Stored securely, rotated on use
- **Token revocation**: Implement blacklist for compromised tokens
- **HTTPS only**: Never send tokens over HTTP

---

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login with credentials | No |
| POST | `/auth/logout` | Logout user | Yes |
| POST | `/auth/refresh` | Refresh tokens | No |
| POST | `/auth/verify-email` | Verify email | No |
| POST | `/auth/resend-verification` | Resend verification | No |
| POST | `/auth/password-reset` | Request password reset | No |
| POST | `/auth/password-reset/confirm` | Confirm password reset | No |
| POST | `/auth/change-password` | Change password | Yes |
| GET | `/auth/me` | Get current user | Yes |

### 2FA Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/2fa/setup` | Setup 2FA | Yes |
| POST | `/auth/2fa/enable` | Enable 2FA | Yes |
| POST | `/auth/2fa/verify` | Verify 2FA code | Yes |
| POST | `/auth/2fa/disable` | Disable 2FA | Yes |

### OAuth Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/auth/oauth/google` | Initiate Google OAuth | No |
| GET | `/auth/oauth/github` | Initiate GitHub OAuth | No |
| GET | `/auth/oauth/callback/google` | Google OAuth callback | No |
| GET | `/auth/oauth/callback/github` | GitHub OAuth callback | No |

---

## Environment Variables

```bash
# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=30

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/oauth/callback/google

GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=https://your-domain.com/auth/oauth/callback/github

# Email Configuration (for verification and reset emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@your-domain.com
```

---

## Troubleshooting

### Common Issues

#### 1. Invalid Token Error

**Problem**: Token verification fails

**Solutions**:
- Check token hasn't expired
- Verify JWT_SECRET matches
- Ensure token format is correct
- Check Authorization header format

#### 2. Rate Limit Exceeded

**Problem**: Too many requests

**Solutions**:
- Wait for rate limit window to reset
- Implement exponential backoff
- Cache tokens instead of requesting new ones
- Use refresh tokens appropriately

#### 3. Email Not Received

**Problem**: Verification/reset email not received

**Solutions**:
- Check spam folder
- Verify email address is correct
- Check SMTP configuration
- Resend verification email

#### 4. 2FA Code Invalid

**Problem**: 2FA code not accepted

**Solutions**:
- Check time synchronization
- Verify secret is correct
- Use backup code if available
- Ensure code is 6 digits

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [JWT.io](https://jwt.io/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)

---

**Last Updated**: 2024
**Maintained By**: Platform Team
**Review Schedule**: Quarterly
