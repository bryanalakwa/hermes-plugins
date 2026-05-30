# hermes-dream-engine Changelog

## v2.1.0 - 2026-05-30

### Added
- Trust scoring integration for dream-generated facts via `trust_scoring` module
- `source_context` and `verification_status` columns now properly set on all dream artifacts
- Awaken-dream state differentiation (facts tagged as `dream_hypothesis` vs `realtime`)

### Changed
- Installer now uses authoritative `MemoryStore` schema from hermes-agent
- Dream facts use source-aware trust computation (0.6 weight for `dream_hypothesis` source)
- Replaced hardcoded trust formula with `compute_trust()` helper

### Technical Details
- Dream artifacts tagged with `source_context='dream_hypothesis'` and `verification_status='dream_hypothesis'`
- Trust scoring weights: realtime=1.0, manual_entry=0.9, dream_hypothesis=0.6, voice_note=0.85
- Verification multipliers: verified=1.0, dream_hypothesis=1.0, needs_verification=0.7