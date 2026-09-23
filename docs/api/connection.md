# Connection & Authentication

## Base URL

```
https://www.acinfinityserver.com
```

All paths below are relative to this host. The HA integration sends every request with a 10 s timeout.

## Headers

| Header | Value | When |
|--------|-------|------|
| `User-Agent` | `okhttp/4.12.0` | always (mimics the Android app) |
| `token` | the `appId` returned by login | every call except login |
| `minversion` | `3.5` | AI-controller writes (`modeAndSetting`); Bruno also sends it on `getdevModeSettingList` |
| `Content-Type` | `application/x-www-form-urlencoded` | POST bodies are form-encoded, not JSON |

## Login

```
POST /api/user/appUserLogin
Content-Type: application/x-www-form-urlencoded

appEmail=<email>&appPasswordl=<password[:25]>
```

- `appPasswordl` — trailing `l` is intentional.
- The API silently rejects passwords longer than **25 characters**; the official app truncates, so truncate to `password[0:25]` before sending.
- Response `data.appId` is the token for all subsequent requests (sent as `token` header). The HA
  integration also passes it as `userId` in the `devInfoListAll` form body.

Example response (from HA test fixtures):

```json
{
  "msg": "Success",
  "code": 200,
  "data": {
    "appId": "11763238626156107487",
    "nickName": "me@example.com",
    "appEmail": "me@example.com",
    "appPasswordl": "<hash>",
    "appUsable": 1,
    "forumUsable": 1,
    "forumRole": 0,
    "appCreateTime": "2023-07-11 20:59:07",
    "appIsanalytics": 0,
    "appIsbugreport": 0,
    "appIsemailrepost": 0,
    "createTime": null
  }
}
```

No token expiry has been observed; the HA integration logs in once at startup and re-logs in only when
`is_logged_in()` is false (i.e. never on its own). A robust client should re-login on a non-200 body code
from an authenticated call and retry once.

## Signed writes (standard controllers)

The login response also returns `secretId`, `requestApp`, `refreshToken` and `timeOut`. According
to the decompiled Android app 2.0.8 (Backroads4Me/homeassistant-acinfinity, branch
`dalinicus-port`), standard controllers (devType 11/18) apply a settings write only when the
request carries the app's signature headers:

```
requestApp: <from login>
version:    2.0.8
requestId:  <unix ms>
sign:       md5( md5(token + version) + md5(secretId + requestApp + requestId) )
```

Unsigned writes are answered `403 "Login Expired"` there. The v2 (`version=2.0`) endpoints
**reject** these headers with the same 403, so signing is per call. AI controllers accept
unsigned writes with `minversion: 3.5`. This server signs standard-family writes; not verified
on our hardware (no standard controller on the account).

## Response envelope

Every endpoint returns HTTP 200 with a JSON envelope:

```json
{ "msg": "Success", "code": 200, "data": ... }
```

Error handling used by the HA client:

| Condition | Meaning |
|-----------|---------|
| HTTP status != 200 | connection problem → `CannotConnect` |
| body `code` != 200 on login | invalid credentials → `InvalidAuth` |
| body `code` != 200 elsewhere | request failed → `RequestFailed(body)` |

## Retry policy (HA `_execute_with_retry`)

The API is known to be flaky. HA retries `CannotConnect`, `RequestFailed`, client errors and timeouts up
to 4 times with exponential backoff (1 s, 2 s, 4 s, 8 s). Auth failures are never retried. All API calls
are serialised through one `asyncio.Lock`.

## Polling

HA default polling interval is 10 s, minimum 5 s. `devInfoListAll` is polled once per account;
`getdevModeSettingList` is polled per controller and per port (port 0 = controller-level settings,
ports 1..`devPortCount` = physical ports).
