# RiffLock MVP Release Checklist

Last updated: 2026-06-22
Source issue: `HAM-134` / `RLD-030`

## Automated validation

- [x] Full pytest suite passes
- [x] Integration tests pass
- [x] Security negative tests pass

## Functional flow checklist

- [x] First launch
- [x] Account setup
- [x] Login without riff 2FA
- [x] Login with riff 2FA
- [x] Failed password lockout
- [x] Failed riff lockout
- [x] Protect single file
- [x] Restore single file
- [x] Protect folder
- [x] Password change
- [x] Restore old file after password change
- [x] App restart keeps database state
- [x] Logs contain no sensitive data

## Manual packaged-app checklist

- [ ] Packaged executable launches
- [ ] First launch works from packaged executable
- [ ] Login works from packaged executable
- [ ] Protect and restore work from packaged executable
- [ ] Riff recording works from packaged executable

## Notes

The manual packaged-app checklist should be completed on a Windows machine after building `dist\RiffLock.exe` from `riff_lock.spec`.
