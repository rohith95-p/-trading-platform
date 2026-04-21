# API Key Security Practices

## Overview

This document outlines the security practices and implementation details for API key management in the Unified Trading Intelligence Platform. API keys are sensitive credentials that provide access to exchange accounts and must be protected with the highest security standards.

## Encryption

### AES-256-GCM

All API keys are encrypted at rest using **AES-256-GCM** (Galois/Counter Mode), which provides:

- **Confidentiality**: 256-bit key strength prevents brute force attacks
- **Authenticity**: Built-in authentication tag detects tampering
- **Integrity**: Any modification to encrypted data is detected during decryption

### Implementation Details

```python
# Encryption process
1. Generate random 96-bit nonce for each encryption operation
2. Encrypt plaintext using AES-256-GCM with nonce
3. Store nonce, ciphertext, and key version separately
4. Never reuse nonces (guaranteed by using random generation)

# Decryption process
1. Retrieve nonce, ciphertext, and key version
2. Decrypt using AES-256-GCM
3. Verify authentication tag (automatic in GCM mode)
4. Return plaintext only if authentication succeeds
```

### Master Key Management

The master encryption key must be:

- **32 bytes (256 bits)** for AES-256
- **Base64-encoded** for storage in environment variables
- **Never committed** to version control
- **Rotated periodically** (recommended: every 90 days)

#### Generating a Master Key

```bash
# Generate a new master key
python -c "from src.api_keys.encryption import APIKeyEncryption; print(APIKeyEncryption.generate_master_key())"

# Set in environment
export ENCRYPTION_KEY="<generated_key>"
```

#### Key Storage

**Development:**
- Store in `.env` file (never commit)
- Use `.env.example` for template

**Production:**
- Use environment variables in hosting platform (Railway, Vercel)
- Use secrets management service (AWS Secrets Manager, HashiCorp Vault)
- Enable automatic rotation if supported

## Key Rotation

### Encryption Key Rotation

The system supports multiple key versions for seamless rotation:

1. **Add new key version** to the encryption service
2. **New encryptions** use the new key version
3. **Old data** remains encrypted with old key version
4. **Gradual migration** re-encrypts data with new key
5. **Remove old key** after all data is migrated

```python
# Example rotation process
encryption = APIKeyEncryption()
encryption.add_key_version(2, new_32_byte_key)

# Re-encrypt existing data
for api_key in db.query(APIKey).all():
    new_nonce, new_ciphertext, new_version = encryption.rotate_key(
        api_key.key_nonce,
        api_key.key_encrypted,
        api_key.key_version
    )
    api_key.key_nonce = new_nonce
    api_key.key_encrypted = new_ciphertext
    api_key.key_version = new_version
```

### API Credential Rotation

Users can rotate their exchange API credentials:

```bash
POST /api/v1/api-keys/{key_id}/rotate
{
  "new_api_key": "NEW_KEY",
  "new_api_secret": "NEW_SECRET",
  "new_passphrase": "NEW_PASS"  # optional
}
```

This replaces the stored credentials while maintaining the same API key record.

## Access Control

### Authentication

All API key endpoints require authentication:

- **JWT tokens** with user ID claim
- **Token expiration** enforced (24 hours)
- **Refresh tokens** for extended sessions

### Authorization

Users can only access their own API keys:

- **User ID verification** on all operations
- **Database-level filtering** by user_id
- **Row-level security** policies in PostgreSQL

### Permissions

API keys have granular permissions:

```json
{
  "read": true,      // View account info, balances, positions
  "trade": false,    // Place and cancel orders
  "withdraw": false  // Withdraw funds (highest risk)
}
```

Default permissions are **read-only** for safety.

## Logging and Auditing

### What We Log

- API key **added** (exchange, permissions)
- API key **updated** (changed fields)
- API key **deleted** (exchange)
- API key **rotated** (exchange)
- API key **validated** (success/failure)
- API key **usage** (timestamp, count)

### What We NEVER Log

- **Unencrypted API keys**
- **Unencrypted API secrets**
- **Unencrypted passphrases**
- **Decrypted credentials** in any form
- **Encryption keys** or nonces

### Audit Log Format

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "api_key_added",
  "details": {
    "exchange": "alpaca",
    "exchange_account_id": "account_123",
    "permissions": {
      "read": true,
      "trade": true,
      "withdraw": false
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Validation

### On Addition

When users add API keys, we validate:

1. **Format validation**: Key and secret are non-empty strings
2. **Exchange validation**: Exchange is in supported list
3. **Passphrase requirement**: Some exchanges require passphrase
4. **Duplicate check**: Prevent duplicate keys for same exchange/account
5. **Test API call**: Verify credentials work (optional)

### Periodic Validation

API keys are validated periodically:

- **On first use**: Before making exchange API calls
- **On demand**: User-triggered validation endpoint
- **Scheduled**: Daily validation of all active keys (optional)

### Validation Errors

Failed validations are recorded:

```python
api_key.is_valid = False
api_key.validation_error = "Invalid credentials"
api_key.last_validated_at = datetime.utcnow()
```

## Expiration Policies

### Automatic Expiration

API keys can have expiration dates:

```python
# Set expiration on creation
AddAPIKeyRequest(
    exchange="alpaca",
    api_key="KEY",
    api_secret="SECRET",
    expires_at=datetime.utcnow() + timedelta(days=90)
)

# Check and mark expired keys
api_key_service.check_expiration(db)
```

### Expiration Handling

- **Expired keys** are marked as invalid
- **Expired keys** cannot be used for trading
- **Expired keys** are excluded from list by default
- **Users notified** before expiration (recommended)

### Recommended Expiration Policies

- **Paper trading**: 1 year
- **Live trading (read-only)**: 90 days
- **Live trading (trade)**: 30 days
- **Live trading (withdraw)**: 7 days

## Usage Tracking

### Metrics Tracked

- **Total usage count**: Number of times credentials were decrypted
- **Last used timestamp**: Most recent usage
- **Usage by day**: Daily usage statistics (optional)

### Usage Limits

Implement rate limiting based on usage:

```python
# Example: Limit to 1000 uses per day
if api_key.usage_count_today > 1000:
    raise ValueError("Daily usage limit exceeded")
```

## Security Best Practices

### For Developers

1. **Never log unencrypted credentials** in any circumstance
2. **Use parameterized queries** to prevent SQL injection
3. **Validate all inputs** before processing
4. **Use HTTPS only** for API communication
5. **Implement rate limiting** on all endpoints
6. **Monitor for suspicious activity** (unusual usage patterns)
7. **Rotate encryption keys** regularly
8. **Keep dependencies updated** for security patches

### For Users

1. **Use read-only permissions** when possible
2. **Never share API keys** with others
3. **Rotate credentials regularly** (every 90 days)
4. **Set expiration dates** on API keys
5. **Monitor usage statistics** for anomalies
6. **Revoke unused keys** immediately
7. **Use separate keys** for different purposes
8. **Enable 2FA** on exchange accounts

### For Operations

1. **Backup encryption keys** securely
2. **Use secrets management** service in production
3. **Enable database encryption** at rest
4. **Use TLS 1.3** for data in transit
5. **Implement monitoring** and alerting
6. **Regular security audits** of code and infrastructure
7. **Incident response plan** for key compromise
8. **Compliance with regulations** (GDPR, SOC 2, etc.)

## Incident Response

### If Encryption Key is Compromised

1. **Immediately rotate** the master encryption key
2. **Re-encrypt all API keys** with new key
3. **Notify affected users** to rotate their exchange credentials
4. **Audit logs** for unauthorized access
5. **Review security** measures and improve

### If API Key is Compromised

1. **Immediately revoke** the compromised key
2. **Notify the user** via email
3. **Audit usage logs** for unauthorized activity
4. **Guide user** to rotate exchange credentials
5. **Investigate** how compromise occurred

## Compliance

### Data Protection

- **GDPR**: Right to erasure (delete API keys on user deletion)
- **CCPA**: Right to know (provide API key usage data)
- **PCI DSS**: Secure storage of sensitive data (encryption)

### Audit Requirements

- **SOC 2**: Comprehensive audit logging
- **ISO 27001**: Security controls and policies
- **FINRA**: Financial industry regulations (if applicable)

## Testing

### Security Testing

1. **Unit tests**: Encryption, decryption, key rotation
2. **Integration tests**: API endpoints, authentication
3. **Penetration testing**: Attempt to extract keys
4. **Fuzzing**: Test with malformed inputs
5. **Code review**: Security-focused review

### Test Coverage

Maintain **80%+ code coverage** for API key management:

```bash
pytest tests/unit/test_api_keys.py --cov=src/api_keys --cov-report=html
```

## References

- [NIST SP 800-38D](https://csrc.nist.gov/publications/detail/sp/800-38d/final): GCM Mode Specification
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [CWE-311](https://cwe.mitre.org/data/definitions/311.html): Missing Encryption of Sensitive Data
- [CWE-312](https://cwe.mitre.org/data/definitions/312.html): Cleartext Storage of Sensitive Information

## Contact

For security concerns or to report vulnerabilities:

- **Email**: security@tradingplatform.com
- **Bug Bounty**: [Link to bug bounty program]
- **PGP Key**: [Link to PGP public key]

---

**Last Updated**: 2024-01-15  
**Version**: 1.0  
**Owner**: Security Team
