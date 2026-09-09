# Fida Field

**Fida Field — Service & Maintenance** is an offline-first Android application for technicians and small field-service teams.

## Test build scope

- Dashboard with open jobs, customers, assets and maintenance attention
- Customers and service sites
- Equipment/assets with tags, serials and maintenance intervals
- Service jobs with diagnosis, work performed, parts, priority and status
- Yearly automatic report numbering (default `FSR-YYYY-00001`)
- Camera photo evidence attached to jobs
- Customer signature capture
- Professional PDF service report generation and Android sharing
- Maintenance planner and service completion logging
- JSON backup and restore of structured local data
- Company identity, default technician, report prefix and light/dark/system theme
- Fully local SQLite storage; no account or server is required for the test build

## Package

`com.fidalix.fidafield`

## Version

`0.9.7-test` (`versionCode 8`)

## Build

Requires JDK 17, Android SDK 36, Android Gradle Plugin 8.10.1 and Gradle 8.11.1.

```bash
gradle :app:assembleDebug
```

The debug APK is created at `app/build/outputs/apk/debug/app-debug.apk`.

## Backup note

The portable ZIP backup includes structured business data, job photos, signatures, relevant settings, and Pro custom-branding preferences/logo when present. Subscription entitlement itself is never copied in backups.


## 0.9.2 roadmap batch
- Daily preventive-maintenance reminder notifications with configurable lead time
- Technician/team directory and job assignment selector
- Asset detail page with full service-job and maintenance history
- Automatic next-service suggestion from maintenance interval when completing work


## 0.9.3 test batch
- Advanced job filters (status, priority, technician and date)
- Customer and site service-history pages
- Quick maintenance completion with recurring next-service suggestion
- CSV export for jobs and assets


## 0.9.4 test signing
Test builds now use a persistent Fida Field test certificate so APKs can update in place. This test key is not the future Google Play production key.

## 0.9.5 commercial foundation
- Free plan foundation: 5 new service reports per month
- Pro entitlement foundation with unlimited reports and CSV export gates
- Test-only Pro entitlement switch for development validation
- Stable commercial product IDs prepared for future Google Play Billing
- Stable per-device cloud identity
- Local sync queue for customer, site, asset, job and technician changes
- No cloud traffic or login yet; all 0.9.5 data remains local
- Database schema upgraded to v3 without deleting existing 0.9.4 data


## 0.9.6 UI / Fidalix branding polish
- Reworked the visual system around the supplied Fidalix charcoal/orange/yellow logo palette
- Refined app bar, accent rule, bottom navigation, cards, badges, buttons, forms, spinners and empty states
- Added proper distinct navigation icons and a Fidalix brand panel
- Improved light/dark theme consistency and Material 3 dialog/control colors
- Updated app icon and PDF report accents to match the Fidalix identity
- Keeps the persistent 0.9.4+ test signing certificate for update-in-place testing


## 0.9.7 Pro custom branding
- Subscriber-only custom branding entry under More
- Custom company logo imported from device storage and copied into app-private storage
- Custom primary, accent and highlight colors using validated `#RRGGBB` values
- Live branding preview before applying colors
- Custom branding applied to app header, controls, navigation accents, cards and generated PDF reports
- Custom logo shown in the workspace and branded PDF header
- Reset to Fidalix defaults at any time
- Branding settings and logo included in portable ZIP backup/restore
- Branding remains stored if Pro expires but is not applied until entitlement is active again
- Android launcher / Play Store app identity remains Fida Field for update and store integrity
