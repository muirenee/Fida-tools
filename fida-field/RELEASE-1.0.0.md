# Fida Field 1.0.0 release baseline

- Package: `com.fidalix.fidafield`
- Version code: `53`
- Version name: `1.0.0`
- Minimum Android SDK: 26
- Target / compile SDK: 36
- Open Edition: internal APK build with `FIDA_OPEN_EDITION=true`
- Google Play Edition: release AAB with `FIDA_OPEN_EDITION=false`
- Password recovery deep link: `fidafield://password-reset`
- Workspace invitation deep link: `fidafield://workspace-invite`
- Cloud backend: Fida Field Supabase project configured through BuildConfig and publishable-key secret
- Existing signing certificate is preserved for upgrade/signature continuity
- API 27 navigation-bar theme attributes are isolated in v27 resources so Android 8.0 / API 26 remains supported

## Release validation

CI for 1.0.0 performs source/branding checks, Android lint, unit-test task, APK build, release AAB build, AAB signature verification, SHA-256 generation, and a production validation report.

## Play Console checks before rollout

Confirm the final store listing, privacy-policy URL, Data safety answers, app access/sign-in instructions, content rating, target audience, countries/regions, pricing/subscription products, and the intended testing/production track before rollout.
