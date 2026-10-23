## NextSet UA 1.3.0

- Invitation-only membership: single-use seven-day links, revocation, member list and suspension/restoration.
- Existing paired owner remains administrator. AI is restricted to that account; payment integration is not enabled.
- Individual diary data, note edits, exports, reminders and weekly reports. Host backup controls require administrator permission.
- Role-specific menus and an account information command.
- Clear-data requests invalidate pending inference and clear personal reminder preferences without resetting membership.
- 124 automated tests pass, including concurrent invitations and cross-account isolation. Real two-account Telegram acceptance remains required.

## NextSet UA 1.2.3

- Optional set, exercise and workout notes, with owner-scoped edit/delete commands and history display.
- Guided and planned set entry accept `70x10; note`; quick exercise entries accept a trailing `; note`.
- Excel/CSV preserve note scopes, and finishing a workout preserves its existing comment.
- Pain wording prompts clarification without automatically changing health status.
- Includes console shutdown and command-navigation fixes. 97 regression tests pass.

## NextSet UA 1.2.2

- Record actual kg and repetitions from per-exercise buttons in an accepted session.
- See recorded sets beside each exercise and finish the session with a guided RIR prompt.
- Invalid input, changed plans and unaccepted sessions cannot silently create actual sets. Submissions append actual values, never prescribed performance.
- 87 regression tests pass, including the complete record-and-finish flow.

## NextSet UA 1.2.1

- Training plans open as short Ukrainian exercise lists instead of automatically sending a PNG calendar.
- Optional **План Excel** (`/planexcel`) exports all weeks with dates, exercises, sets, repetitions, kg and repetitions in reserve.
- Working kg are included only for today's matching session in the accepted block. Missing and future weights remain unspecified; PRs are never copied as working weights.
- The reference workbook influences layout only. Generated exercises, weekly guidance, substitutions and actual progress tracking are preserved.
- 83 regression tests pass, including text-only delivery, weight provenance and safe Excel text cells. The Windows executable passes its packaged self-check.

Keep your existing `data/` folder when upgrading. Model inference is not needed just to view or export a saved plan.

## NextSet UA 1.2.0

- Simpler Ukrainian home screen, guided profile and actual-PR entry, and support for `/profile:` text.
- Ten method cards grouped by goal, with focus, suitability, practical pros/cons, progression and primary sources. Choosing a different method requires confirmation.
- Eight-week blocks by default (4–8 supported) and a dated PNG calendar with 24 training slots. Plans and actual progress remain separate; 56-day progress charts are available.
- Coaching requests run in the background with elapsed time, status, cancellation, persisted results, stale-data protection and explicit failure/interruption states.
- Clear `nextset/` package structure, separate tests, canonical SQLite module and architecture documentation. Existing user data needs no schema migration.
- Windows system TLS trust for both Telegram transports, retaining certificate and hostname checks.

Keep your existing `data/` folder when upgrading. Local Qwen remains optional and separately installed; its weights are not fine-tuned by this release.

## NextSet UA 1.1.1

Download **NextSet-UA-Windows.zip**, extract it, and open **NextSet.exe**.
Python is included. First run asks for your own Telegram bot token and prints a private pairing link.

- Ukrainian Telegram menus, prompts and exercise catalogue.
- Sets, reps and kilograms with full history and quick text input.
- Body measurements, progress charts and optional inactivity reminders.
- Local SQLite storage and Excel/CSV exports.
- Optional Ollama text extraction with explicit confirmation before saving.
- Experimental local research-grounded coaching (RAG): seven evidence summaries, five program orientations for experienced lifters, PR/profile/history context, cited proposals and explicit plan acceptance. This is not model fine-tuning; application guards are tested against the real local model, while scientific suitability still requires manual review.
- Illness/pain pauses, missed-session notes, actual-session feedback and an optional light fourth day. See PROGRAMS.md for exact constraints and limitations.
- English setup, user guide and troubleshooting documentation.
- AI-generated 4–6 week blocks with three stable recurring sessions and explicit approval.
- Pre-workout button check-in, per-exercise RIR/pain/difficulty feedback and equipment substitutions with independent load references.
- Actual-data weekly reports, optional Sunday delivery and source-grounded weekly interpretation.
- Daily consistent SQLite backups, 14-archive retention and offline RESTORE.cmd with checksum/integrity checks and a pre-restore snapshot.
- EVALUATE_AI.cmd for real local Qwen evaluation on six synthetic cases; output reports distinguish app acceptance from scientific correctness.

Windows 10/11 x64. Keep your PC awake and the app running. AI models are not bundled. The executable is unsigned. This release contains no bot token, personal data or preconfigured account.

For upgrades, preserve your private **data/** folder. Stop the old instance before starting another one with the same bot token.

- Qwen3 4B Instruct default, explicitly unit-labelled profiles, Ukrainian prose rejection, balanced whole-body block checks and application-side load arithmetic.
- Incompatible time budgets are rejected before inference; recovery keeps the approved exercises within a reduced set budget.
