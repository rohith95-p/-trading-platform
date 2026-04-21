# Session Management Documentation

## Overview

The session management system provides secure tracking and validation of user sessions with JWT tokens. It implements absolute expiration, idle timeouts, concurrent session limits, and activity tracking.

## Features

- **Session Creation**: Automatic session creation on user login
- **Token Validation**: JWT token validation with session verification
- **Expiration Management**: 
  - Absolute expiration: 24 hours from creation
  - Idle timeout: 2 hours of inactivity
- **Concurrent Session Limits**: Maximum 5 active sessions per user
- **Activity Tracking**: Last activity timestamp updated on each request
- **Session Cleanup**: Automatic cleanup of expired sessions
- **Security**: Token hashing (SHA-256) for storage

## Architecture

### Database Schema

```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  token_hash TEXT UNIQUE,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP,
  last_activity_at TIMESTAMP,
  expires_at TIMESTAMP,
  is_active BOOLEAN,
  metadata JSONB
);
```

### Components

1. **SessionService**: Core service for session management
2. **SessionMiddleware**: FastAPI middleware for automatic session validation
3. **API Endpoints**: RESTful endpoints for session operations
4. **Database Functions**: PostgreSQL functions for cleanup and limits

## Usage

### Creating a Session (Login)

Sessions are automatically created when users log in:

```python
from src.auth.auth_service import AuthService

auth_service = AuthService()
token_response = await auth_service.login_user(
    login=UserLogin(email="user@example.com", password="password"),
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0"
)
```

### Validating a Session

The `SessionMiddleware` automatically validates sessions on each request:

```python
from fastapi import FastAPI, Request
from src.session.middleware import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, db_connection=db)

@app.get("/protected")
async def protected_route(request: Request):
    user_id = request.state.user_id
    session_id = request.state.session_id
    return {"user_id": user_id, "session_id": session_id}
```

### Manual Session Validation

```python
from src.session.session_service import SessionService

session_service = SessionService(db)
result = await session_service.validate_session(
    token="jwt_access_token",
    update_activity=True
)

if result.is_valid:
    print(f"Valid session for user {result.user_id}")
else:
    print(f"Invalid session: {result.reason}")
```

### Listing User Sessions

```python
sessions = await session_service.list_user_sessions(
    user_id="user-uuid",
    include_inactive=False
)

print(f"Total sessions: {sessions.total}")
print(f"Active sessions: {sessions.active}")
for session in sessions.sessions:
    print(f"Session {session.id}: {session.ip_address}")
```

### Logging Out

#### Logout Specific Session

```python
await session_service.logout_session(
    session_id="session-uuid",
    user_id="user-uuid"
)
```

#### Logout All Sessions

```python
count = await session_service.logout_all_sessions(user_id="user-uuid")
print(f"Logged out {count} sessions")
```

### Refreshing a Session

```python
session = await session_service.refresh_session(
    session_id="session-uuid",
    user_id="user-uuid"
)
print(f"Session expires at: {session.expires_at}")
```

## API Endpoints

### List Sessions

```http
GET /api/v1/sessions?include_inactive=false
Authorization: Bearer <token>
```

Response:
```json
{
  "sessions": [
    {
      "id": "session-uuid",
      "user_id": "user-uuid",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0",
      "created_at": "2024-01-01T00:00:00Z",
      "last_activity_at": "2024-01-01T12:00:00Z",
      "expires_at": "2024-01-02T00:00:00Z",
      "is_active": true,
      "metadata": {}
    }
  ],
  "total": 1,
  "active": 1
}
```

### Get Session Details

```http
GET /api/v1/sessions/{session_id}
Authorization: Bearer <token>
```

### Logout Session

```http
DELETE /api/v1/sessions/{session_id}
Authorization: Bearer <token>
```

### Logout All Sessions

```http
DELETE /api/v1/sessions
Authorization: Bearer <token>
```

### Refresh Session

```http
POST /api/v1/sessions/refresh
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "session-uuid"
}
```

### Get Current Session Info

```http
GET /api/v1/sessions/current/info
Authorization: Bearer <token>
```

## Configuration

### Environment Variables

```bash
# JWT Configuration (affects session expiration)
JWT_EXPIRATION_HOURS=24
JWT_SECRET=your-secret-key

# Session Configuration (in SessionService)
ABSOLUTE_EXPIRATION_HOURS=24  # 24 hours from creation
IDLE_TIMEOUT_HOURS=2          # 2 hours of inactivity
MAX_SESSIONS_PER_USER=5       # Maximum concurrent sessions
```

### Customizing Session Limits

To change session limits, modify the constants in `SessionService`:

```python
class SessionService:
    ABSOLUTE_EXPIRATION_HOURS = 24
    IDLE_TIMEOUT_HOURS = 2
    MAX_SESSIONS_PER_USER = 5
```

## Security Considerations

### Token Hashing

JWT tokens are hashed using SHA-256 before storage:

```python
token_hash = hashlib.sha256(token.encode()).hexdigest()
```

This ensures that even if the database is compromised, tokens cannot be used directly.

### Session Validation

Sessions are validated on each request:

1. JWT token signature verification
2. Session existence check
3. Absolute expiration check
4. Idle timeout check
5. Activity timestamp update

### Concurrent Session Limits

When a user exceeds the maximum session limit (5), the oldest session is automatically deactivated:

```sql
CREATE TRIGGER enforce_sessions_limit BEFORE INSERT ON sessions
  FOR EACH ROW EXECUTE FUNCTION enforce_session_limit();
```

### IP Address and User Agent Tracking

Sessions track client IP address and user agent for security monitoring:

```python
session = await session_service.create_session(
    user_id=user_id,
    token=token,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0"
)
```

## Background Tasks

### Automatic Session Cleanup

Expired sessions should be cleaned up periodically using a background task:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def cleanup_sessions():
    session_service = SessionService(db)
    count = await session_service.cleanup_expired_sessions()
    logger.info(f"Cleaned up {count} expired sessions")

# Run every hour
scheduler.add_job(cleanup_sessions, 'interval', hours=1)
scheduler.start()
```

The cleanup function:
1. Marks expired sessions as inactive
2. Deletes sessions inactive for more than 30 days

## Monitoring

### Session Metrics

Track these metrics for monitoring:

- **Active sessions per user**: Monitor for unusual activity
- **Session creation rate**: Detect potential attacks
- **Session expiration rate**: Understand user behavior
- **Failed validation attempts**: Security monitoring

### Logging

Session events are logged:

```python
logger.info(f"Created session {session.id} for user {user_id}")
logger.info(f"Deactivated session {session_id}")
logger.warning(f"Invalid session: {validation_result.reason}")
```

### Audit Trail

Session events are automatically logged to the `audit_log` table via triggers:

```sql
CREATE TRIGGER audit_sessions AFTER INSERT OR UPDATE OR DELETE ON sessions
  FOR EACH ROW EXECUTE FUNCTION log_audit_event();
```

## Testing

### Unit Tests

Run session management tests:

```bash
pytest tests/unit/test_sessions.py -v
```

### Test Coverage

Tests cover:
- Session creation
- Token hashing
- Session validation (success, expired, idle)
- Logout (single and all sessions)
- Session listing
- Session refresh
- Concurrent session limits
- Error handling

## Troubleshooting

### Session Not Found

**Symptom**: "Session not found or inactive" error

**Causes**:
1. Session expired (absolute or idle timeout)
2. User logged out
3. Session limit exceeded (oldest session deactivated)

**Solution**: User should log in again to create a new session

### Session Expired (Absolute Timeout)

**Symptom**: "Session expired (absolute timeout)" error

**Cause**: Session older than 24 hours

**Solution**: User should log in again

### Session Expired (Idle Timeout)

**Symptom**: "Session expired (idle timeout)" error

**Cause**: No activity for more than 2 hours

**Solution**: User should log in again

### Too Many Sessions

**Symptom**: Oldest session automatically deactivated

**Cause**: User has more than 5 active sessions

**Solution**: 
- User can manually logout old sessions
- System automatically deactivates oldest session

## Best Practices

1. **Always use HTTPS**: Protect tokens in transit
2. **Implement rate limiting**: Prevent brute force attacks
3. **Monitor session activity**: Detect suspicious patterns
4. **Regular cleanup**: Run cleanup task hourly
5. **Secure token storage**: Never log or expose tokens
6. **Use middleware**: Automatic validation on all routes
7. **Track IP and user agent**: Security monitoring
8. **Implement CSRF protection**: Additional security layer

## Migration

To add session management to an existing system:

1. Run the migration script:
```bash
psql -d your_database -f sql/migrations/004_add_sessions_table.sql
```

2. Update auth service to create sessions on login

3. Add session middleware to FastAPI app:
```python
app.add_middleware(SessionMiddleware, db_connection=db)
```

4. Update logout to invalidate sessions

5. Set up background cleanup task

## Future Enhancements

Potential improvements:

1. **Redis caching**: Cache active sessions for faster validation
2. **Device fingerprinting**: Enhanced security tracking
3. **Session notifications**: Alert users of new sessions
4. **Geolocation tracking**: Track session locations
5. **Session transfer**: Transfer session between devices
6. **Admin session management**: Allow admins to manage user sessions
7. **Session analytics**: Detailed session usage analytics

## References

- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Session Management](https://owasp.org/www-community/Session_Management_Cheat_Sheet)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
