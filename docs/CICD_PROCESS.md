# CI/CD Process Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Unified Trading Intelligence Platform.

## Table of Contents

1. [Overview](#overview)
2. [Workflows](#workflows)
3. [Environments](#environments)
4. [Secrets Configuration](#secrets-configuration)
5. [Deployment Process](#deployment-process)
6. [Monitoring and Notifications](#monitoring-and-notifications)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The CI/CD pipeline is implemented using GitHub Actions and consists of multiple workflows that handle:

- Code quality checks (linting, type checking)
- Automated testing (unit, integration, E2E)
- Code coverage reporting
- Automated deployment to staging
- Manual deployment to production with approval
- Notifications and monitoring

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Code Push/PR                             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌───────────────┐
│   Linting     │         │ Type Checking │
└───────┬───────┘         └───────┬───────┘
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌───────────────┐
│  Unit Tests   │         │   Coverage    │
└───────┬───────┘         └───────┬───────┘
        │                         │
        └────────────┬────────────┘
                     │
                     ▼
          ┌──────────────────┐
          │ Integration Tests│
          └─────────┬────────┘
                    │
                    ▼
          ┌──────────────────┐
          │ Deploy to Staging│ (auto on develop)
          └─────────┬────────┘
                    │
                    ▼
          ┌──────────────────┐
          │  Smoke Tests     │
          └─────────┬────────┘
                    │
                    ▼
          ┌──────────────────┐
          │Deploy to Prod    │ (manual approval)
          └─────────┬────────┘
                    │
                    ▼
          ┌──────────────────┐
          │ Create Release   │
          └──────────────────┘
```

---

## Workflows

### 1. Linting (`lint.yml`)

**Triggers**: Push to main/develop/staging, Pull requests to main/develop

**Jobs**:
- **python-lint**: Runs Black, isort, and Pylint on Python code
- **frontend-lint**: Runs ESLint and Prettier on TypeScript/JavaScript code

**Duration**: ~2-3 minutes

**Example**:
```bash
# Manually run linting locally
black --check src/ tests/
pylint src/
cd frontend && npm run lint
```

### 2. Type Checking (`type-check.yml`)

**Triggers**: Push to main/develop/staging, Pull requests to main/develop

**Jobs**:
- **python-type-check**: Runs Mypy on Python code
- **frontend-type-check**: Runs TypeScript compiler in check mode

**Duration**: ~2-3 minutes

**Example**:
```bash
# Manually run type checking locally
mypy src/
cd frontend && npx tsc --noEmit
```

### 3. Unit Tests (`unit-tests.yml`)

**Triggers**: Push to main/develop/staging, Pull requests to main/develop

**Jobs**:
- **backend-unit-tests**: Runs pytest on unit tests with PostgreSQL and Redis services
- **frontend-unit-tests**: Runs Jest tests on frontend components

**Duration**: ~5-7 minutes

**Services**:
- PostgreSQL 15
- Redis 7

**Example**:
```bash
# Manually run unit tests locally
pytest tests/unit/ -v
cd frontend && npm test
```

### 4. Integration Tests (`integration-tests.yml`)

**Triggers**: Push to main/develop/staging, Pull requests to main/develop

**Jobs**:
- **backend-integration-tests**: Tests API endpoints and database operations
- **frontend-integration-tests**: Tests component integration
- **e2e-tests**: End-to-end tests (only on main/develop pushes)

**Duration**: ~10-15 minutes

**Example**:
```bash
# Manually run integration tests locally
pytest tests/integration/ -v
```

### 5. Code Coverage (`coverage.yml`)

**Triggers**: Push to main/develop, Pull requests to main/develop

**Jobs**:
- **backend-coverage**: Generates Python code coverage report
- **frontend-coverage**: Generates JavaScript/TypeScript coverage report
- **coverage-summary**: Combines and uploads coverage reports

**Coverage Requirements**:
- Minimum: 80%
- Target: 90%+

**Artifacts**:
- HTML coverage reports (retained for 30 days)
- Codecov integration
- PR comments with coverage changes

**Example**:
```bash
# Manually generate coverage locally
pytest tests/ --cov=src --cov-report=html
cd frontend && npm test -- --coverage
```

### 6. Deploy to Staging (`deploy-staging.yml`)

**Triggers**: Push to develop branch, Manual workflow dispatch

**Jobs**:
- **deploy-backend-staging**: Deploys backend to Railway staging environment
- **deploy-frontend-staging**: Deploys frontend to Vercel preview environment
- **run-smoke-tests**: Runs basic smoke tests on staging
- **notify-deployment**: Sends Slack notification

**Duration**: ~5-10 minutes

**Environments**:
- Backend: https://trading-platform-api-staging.railway.app
- Frontend: https://trading-platform-staging.vercel.app

### 7. Deploy to Production (`deploy-production.yml`)

**Triggers**: Manual workflow dispatch only

**Required Inputs**:
- **version**: Version tag (e.g., v1.0.0)
- **confirm**: Must type "DEPLOY" to confirm

**Jobs**:
- **validate-input**: Validates deployment inputs
- **pre-deployment-checks**: Runs all tests and checks coverage
- **deploy-backend-production**: Deploys backend to Railway production
- **deploy-frontend-production**: Deploys frontend to Vercel production
- **run-production-smoke-tests**: Runs smoke tests on production
- **create-release**: Creates GitHub release with changelog
- **notify-deployment**: Sends Slack notification
- **rollback-on-failure**: Alerts team if deployment fails

**Duration**: ~15-20 minutes

**Environments**:
- Backend: https://trading-platform-api-production.railway.app
- Frontend: https://trading-platform.vercel.app

---

## Environments

### Development (Local)

- **Purpose**: Local development and testing
- **Database**: Docker PostgreSQL container
- **Redis**: Docker Redis container
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000

### Staging

- **Purpose**: Pre-production testing and validation
- **Database**: Supabase staging project
- **Redis**: Railway Redis staging
- **Backend**: https://trading-platform-api-staging.railway.app
- **Frontend**: https://trading-platform-staging.vercel.app
- **Deployment**: Automatic on push to `develop` branch

### Production

- **Purpose**: Live production environment
- **Database**: Supabase production project
- **Redis**: Railway Redis production
- **Backend**: https://trading-platform-api-production.railway.app
- **Frontend**: https://trading-platform.vercel.app
- **Deployment**: Manual with approval required

---

## Secrets Configuration

### Required GitHub Secrets

#### Railway Secrets
```
RAILWAY_STAGING_TOKEN          # Railway API token for staging
RAILWAY_STAGING_PROJECT_ID     # Railway project ID for staging
RAILWAY_PRODUCTION_TOKEN       # Railway API token for production
RAILWAY_PRODUCTION_PROJECT_ID  # Railway project ID for production
```

#### Vercel Secrets
```
VERCEL_TOKEN                   # Vercel API token
VERCEL_ORG_ID                  # Vercel organization ID
VERCEL_PROJECT_ID              # Vercel project ID
```

#### Code Coverage Secrets
```
CODECOV_TOKEN                  # Codecov API token (optional)
```

#### Notification Secrets
```
SLACK_WEBHOOK_URL              # Slack webhook URL for notifications
```

#### API Keys (for integration tests)
```
ANTHROPIC_API_KEY              # Claude API key (optional for tests)
```

### Setting Up Secrets

1. Go to GitHub repository settings
2. Navigate to "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add each secret with its value

**Example**:
```bash
# Get Railway token
railway login
railway whoami --token

# Get Vercel token
vercel login
vercel whoami --token
```

---

## Deployment Process

### Deploying to Staging

Staging deployments happen automatically when code is pushed to the `develop` branch.

**Process**:
1. Create feature branch from `develop`
2. Make changes and commit
3. Push to GitHub
4. Create pull request to `develop`
5. Wait for CI checks to pass
6. Merge pull request
7. Automatic deployment to staging begins
8. Smoke tests run on staging
9. Slack notification sent

**Manual Staging Deployment**:
```bash
# Via GitHub UI
1. Go to Actions tab
2. Select "Deploy to Staging" workflow
3. Click "Run workflow"
4. Select branch (usually develop)
5. Click "Run workflow"
```

### Deploying to Production

Production deployments require manual approval and must be triggered explicitly.

**Prerequisites**:
- All tests passing on `main` branch
- Code reviewed and approved
- Staging deployment successful
- Version number decided (semantic versioning)

**Process**:
1. Ensure `main` branch is up to date
2. Go to GitHub Actions tab
3. Select "Deploy to Production" workflow
4. Click "Run workflow"
5. Enter version (e.g., v1.0.0)
6. Type "DEPLOY" to confirm
7. Click "Run workflow"
8. Monitor deployment progress
9. Verify smoke tests pass
10. Check Slack notification
11. Verify production site is working

**Post-Deployment**:
- GitHub release created automatically
- Changelog generated from commits
- Slack notification sent to team
- Monitor error rates and performance

**Rollback Process**:
If deployment fails:
1. Check Slack alert
2. Review workflow logs
3. Identify issue
4. Fix issue or revert changes
5. Deploy previous version if needed

---

## Monitoring and Notifications

### Slack Notifications

Notifications are sent for:
- ✅ Successful staging deployments
- ✅ Successful production deployments
- ❌ Failed deployments
- ⚠️ Rollback alerts

**Notification Format**:
```
Production Deployment Success

Version: v1.0.0
Backend: success
Frontend: success
Smoke Tests: success
Release: success

[View Workflow Run] [Visit Production Site]
```

### Test Result Reporting

- **Coverage Reports**: Uploaded as artifacts, retained for 30 days
- **PR Comments**: Coverage changes commented on pull requests
- **Codecov Integration**: Coverage trends tracked over time
- **Test Summaries**: Displayed in workflow run summary

### Health Checks

Automated health checks run after each deployment:
- Backend: `GET /health`
- Frontend: `GET /`
- Retries: 5 attempts with 10-second intervals
- Timeout: 50 seconds total

---

## Troubleshooting

### Common Issues

#### 1. Linting Failures

**Problem**: Black or Pylint checks fail

**Solution**:
```bash
# Format code locally
black src/ tests/
isort src/ tests/

# Check for remaining issues
pylint src/
```

#### 2. Type Checking Failures

**Problem**: Mypy or TypeScript errors

**Solution**:
```bash
# Run type checking locally
mypy src/
cd frontend && npx tsc --noEmit

# Add type hints or ignore specific errors
# src/example.py
def my_function(x: int) -> str:  # type: ignore
    return str(x)
```

#### 3. Test Failures

**Problem**: Tests fail in CI but pass locally

**Solution**:
```bash
# Ensure services are running
docker-compose up -d postgres redis

# Run tests with same environment
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/test_db \
REDIS_URL=redis://localhost:6379 \
pytest tests/ -v
```

#### 4. Coverage Below Threshold

**Problem**: Coverage is below 80%

**Solution**:
```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html

# Open htmlcov/index.html to see uncovered lines
# Add tests for uncovered code
```

#### 5. Deployment Failures

**Problem**: Deployment to Railway or Vercel fails

**Solution**:
```bash
# Check Railway logs
railway logs --service backend --environment production

# Check Vercel logs
vercel logs <deployment-url>

# Verify secrets are set correctly
# Check environment variables in Railway/Vercel dashboard
```

#### 6. Smoke Tests Fail

**Problem**: Smoke tests fail after deployment

**Solution**:
```bash
# Check health endpoint manually
curl https://trading-platform-api-production.railway.app/health

# Check application logs
railway logs --service backend --environment production

# Verify database connection
# Check environment variables
```

### Getting Help

If you encounter issues not covered here:

1. Check workflow logs in GitHub Actions
2. Review error messages carefully
3. Search existing GitHub issues
4. Ask in team Slack channel
5. Create new GitHub issue with:
   - Workflow name
   - Error message
   - Steps to reproduce
   - Environment details

---

## Best Practices

### For Developers

1. **Run checks locally before pushing**:
   ```bash
   black src/ tests/
   pylint src/
   mypy src/
   pytest tests/
   ```

2. **Keep tests fast**: Unit tests should run in < 5 minutes

3. **Write meaningful commit messages**: Used in release changelogs

4. **Update tests with code changes**: Maintain 80%+ coverage

5. **Test on staging before production**: Always verify on staging first

### For Reviewers

1. **Check CI status**: All checks must pass before merging

2. **Review coverage changes**: Ensure new code is tested

3. **Verify deployment readiness**: Confirm changes are safe for production

4. **Test manually if needed**: For critical changes, test on staging

### For Deployers

1. **Use semantic versioning**: v1.0.0, v1.1.0, v2.0.0

2. **Write release notes**: Document changes for users

3. **Monitor after deployment**: Watch for errors in first 30 minutes

4. **Have rollback plan**: Know how to revert if needed

5. **Communicate with team**: Announce deployments in Slack

---

## Workflow Maintenance

### Updating Workflows

1. Edit workflow files in `.github/workflows/`
2. Test changes on feature branch
3. Create pull request
4. Review and merge to main

### Adding New Workflows

1. Create new YAML file in `.github/workflows/`
2. Define triggers, jobs, and steps
3. Test thoroughly
4. Document in this file

### Removing Workflows

1. Delete workflow file
2. Update documentation
3. Clean up related secrets if no longer needed

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Railway Documentation](https://docs.railway.app)
- [Vercel Documentation](https://vercel.com/docs)
- [Codecov Documentation](https://docs.codecov.com)
- [Slack Webhooks](https://api.slack.com/messaging/webhooks)

---

**Last Updated**: 2024
**Maintained By**: Platform Team
