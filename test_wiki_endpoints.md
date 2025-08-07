# Wiki API Endpoints - Optional Authentication

## Overview

The wiki endpoints now support **optional authentication**, allowing both authenticated and unauthenticated users to access wikis based on their type:

- **Authenticated users**: Can access their own wikis (both email uploads and user projects)
- **Unauthenticated users**: Can only access email upload wikis

## Test Commands

### 1. Test Wiki Generation (Authenticated)

```bash
# First, get an access token by signing in
curl -X POST "http://localhost:8000/api/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'

# Use the returned access_token to start wiki generation
curl -X POST "http://localhost:8000/api/wiki/runs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "index_run_id": "668ecac8-beb5-4f94-94d6-eee8c771044d"
  }'
```

### 2. Test Wiki Generation (Unauthenticated - Email Upload Only)

```bash
# For email upload wikis, you can access without authentication
curl -X GET "http://localhost:8000/api/wiki/runs/668ecac8-beb5-4f94-94d6-eee8c771044d" \
  -H "Content-Type: application/json"
```

### 3. List Wiki Runs (Authenticated)

```bash
curl -X GET "http://localhost:8000/api/wiki/runs/668ecac8-beb5-4f94-94d6-eee8c771044d" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. List Wiki Runs (Unauthenticated - Email Upload Only)

```bash
# Only works for email upload wikis
curl -X GET "http://localhost:8000/api/wiki/runs/668ecac8-beb5-4f94-94d6-eee8c771044d"
```

### 5. Get Wiki Pages (Authenticated)

```bash
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/pages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Get Wiki Pages (Unauthenticated - Email Upload Only)

```bash
# Only works for email upload wikis
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/pages"
```

### 7. Get Wiki Page Content (Authenticated)

```bash
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/pages/Projektoversigt.md" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 8. Get Wiki Page Content (Unauthenticated - Email Upload Only)

```bash
# Only works for email upload wikis
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/pages/Projektoversigt.md"
```

### 9. Get Wiki Metadata (Authenticated)

```bash
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/metadata" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 10. Get Wiki Metadata (Unauthenticated - Email Upload Only)

```bash
# Only works for email upload wikis
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/metadata"
```

### 11. Get Wiki Run Status (Authenticated)

```bash
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 12. Get Wiki Run Status (Unauthenticated - Email Upload Only)

```bash
# Only works for email upload wikis
curl -X GET "http://localhost:8000/api/wiki/runs/WIKI_RUN_ID/status"
```

## Access Control Rules

### For Authenticated Users:
- ✅ Can access their own wikis (both email uploads and user projects)
- ✅ Can create new wiki generations for their indexing runs
- ✅ Can delete their own wiki runs
- ❌ Cannot access other users' wikis

### For Unauthenticated Users:
- ✅ Can access email upload wikis (no authentication required)
- ❌ Cannot access user project wikis (authentication required)
- ❌ Cannot create new wiki generations
- ❌ Cannot delete wiki runs

## Error Responses

### 401 Unauthorized (when authentication is required)
```json
{
  "detail": "Invalid authentication credentials"
}
```

### 403 Forbidden (when access is denied)
```json
{
  "detail": "Access denied: This wiki run does not belong to you"
}
```

### 403 Forbidden (when authentication is required for user projects)
```json
{
  "detail": "Access denied: Authentication required for user project wikis"
}
```

### 404 Not Found
```json
{
  "detail": "Wiki run not found"
}
```

## Example Usage Scenarios

### Scenario 1: Email Upload User
1. User uploads documents via email
2. Receives email with wiki generation link
3. Can access wiki without creating account
4. Can view all wiki pages and content

### Scenario 2: Authenticated User
1. User signs up/logs in
2. Uploads documents through web interface
3. Can access their wikis with authentication
4. Can create new wiki generations
5. Can delete their wiki runs

### Scenario 3: Mixed Access
1. User has both email uploads and user projects
2. Can access email upload wikis without authentication
3. Must authenticate to access user project wikis
4. All access is properly controlled and validated 