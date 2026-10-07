# Training tools

The bot speaks Ukrainian. These instructions are in English. Diary, check-in, feedback, reports and backups work without Qwen. Generating blocks, sessions, substitutions and explanations requires local Ollama.

## A normal training day

1. Choose an orientation with `/programs` and enter your profile and recent, actually performed PRs with `/coachhelp`. Enter four years of experience if applicable. Measurements belong in `/measure`; they never determine your strength.
2. Request `/block 4`, `/block 5` or `/block 6`. Qwen proposes three recurring sessions, exercise IDs, set/repetition/RIR ranges and weekly guidance. Review them, then `/blockconfirm` or `/blockreject`. You can continue using individual sessions without a block.
3. Press **✅ Перед тренуванням** or send `/checkin`. Answer the four button prompts: sleep hours, energy 1–5, soreness 0–5, available minutes. Decimal sleep hours are allowed. A check-in clears an old session proposal but cannot lift an illness/pain pause.
4. Request `/plan`. Within an accepted block, exercise selection and ranges stay stable. Qwen adapts the next proposal using actual history, effort, check-in and weekly guidance. Review the weights and explanations; `/planconfirm` accepts the session. A plan that violates its blueprint or app guards is rejected, never silently replaced by a hardcoded routine.
5. Log actual sets, for example `Жим лежачи 3x8 60 кг`. Add exercise feedback: `/feedback Жим лежачи; 2; ні; 4; останній підхід важкий`. Fields are exercise, lowest RIR 0–5, pain `так`/`ні`, difficulty 1–5, optional note. Feedback requires today's saved sets of that exercise. Reported pain pauses coaching. Feedback is separate from a strength PR.
6. `/done 3` finishes the accepted session using actual saved sets. The lower of session RIR and exercise RIR is retained. Completed main sessions advance the block; skips and extra sessions do not. Blocks represent 12–18 completed main sessions, so a missed week extends their calendar duration.

## Changing equipment

`/swap Жим лежачи; лавка зайнята` asks Qwen to replace one exercise with a catalog alternative of the same movement. The rest of the session stays intact. Review the result; `/swapconfirm` accepts the substitution, `/swapreject` discards it. Accept the updated full session with `/planconfirm`.

Substitutions persist for that recurring session within an approved block. A variant has its own strength history: barbell kilograms are never copied onto dumbbells or machines. Without a recent PR or actual reference for the new ID, kilograms remain unspecified and require warm-up calibration. A substitution is a practical proposal, not proof of physiological equivalence. Use `/status біль` for pain; substitutions are not pain treatment.

## Skips, illness and an extra day

`/skip робота` records a missed session and leaves the sequence unchanged. `/status хворію` or `/status біль` pauses coaching. Explicit recovery remains required; a positive check-in cannot bypass it. `/extra` remains an optional light session after three eligible main sessions, subject to the existing recovery and timing guards. It never advances or changes the block.

## Weekly reports

`/weekly` shows the last seven calendar days including today: recorded sessions, finished sessions, work sets, recorded kg×reps volume and approximate Epley estimates from sets of 1–10 repetitions. Estimates compare matching exercise names with the previous seven days; they are not new measured PRs. Available measurement points from 35 days are displayed. Stable names, technique and equipment are necessary for useful comparisons.

`/weeklyai` asks Qwen to interpret those facts with local sources. It does not modify your program. `/weeklyremind on` enables a Sunday report after 18:00 according to your PC's local clock; `/weeklyremind off` disables it. It sends once that Sunday while the app is running. No automatic model inference occurs. If the PC is off all Sunday evening, that report is not sent later.

## Backups and recovery

The running app makes one local backup per day and retains the latest 14 archives. `/backup` creates an additional snapshot; `/backups` lists available archives. SQLite's backup API makes a consistent snapshot even during logging. Each archive contains the database and a checksum manifest, never the `.env` bot token. The database still contains personal workout data and pairing/settings; keep backups private.

To restore: stop NextSet, double-click **RESTORE.cmd**, choose the archive and type `RESTORE` after reviewing the selection. Restoration checks archive entries, checksum, SQLite integrity and required tables first. It saves your current database before replacement and preserves your local token. The same instance lock used by the bot prevents restoration while the bot is running.

To move PCs: copy a `nextset-*.zip` backup into the new app's `data/backups/`, run RESTORE.cmd, then NextSet.exe. Enter your token on that computer if it has no `.env`. Keep the old copy stopped. Alternatively copy the complete `data/` folder while stopped; that method includes private credentials.

## Real model evaluation

After installing the model and starting Ollama, run **EVALUATE_AI.cmd**. It sends synthetic examples only, never your workout database, to the local model: an experienced athlete, missing strength references, recovery, a four-week block, an equipment swap and an evidence question. Reports go to `data/evaluation/`.

The report preserves model ID, corpus hash, durations and accepted/rejected outputs. Acceptance means the output passed application guards; it does not prove scientific correctness, source entailment, Ukrainian fluency or individual suitability. Read the report and manually review all outputs. Missing Ollama is reported as unavailable, not a passing test. Coaching remains experimental.

## Transparent app guards

The catalog describes exercise identities and movements; it does not prescribe workouts. Qwen chooses blocks, exercises, sets, reps, RIR and a relative load fraction (0.25–1.0). The app performs the arithmetic: `reference / (1 + (reps + RIR) / 30) × fraction`, then applies any conservative fatigue factor and rounds down to your plate increment. Without an exercise-specific fresh reference, kilograms remain unspecified. This numerical tool prevents language-model arithmetic errors; it is not an automatic fixed workout or optimal-load guarantee. Code verifies structure and controls saving. Recovery limits and explicit approvals remain as described in [PROGRAMS.md](PROGRAMS.md).

A same-day check-in with energy ≤2, soreness ≥4 or sleep <5 hours applies the existing conservative 0.8 load-ceiling factor. Available time caps work sets using an approximate `floor((minutes - 10) / 2)` budget. These are transparent product safeguards, not evidence of optimal recovery or precise workout duration. An incompatible block/time combination is rejected for review rather than silently reshaped.

## Topic scope and stored knowledge

The evidence corpus is a persistent reviewed file, not automatic learning from chats. Your profile, actual sets and effort feedback are stored separately and inform personal context. Off-topic questions without training vocabulary and common mixed-topic requests are refused before model inference. Other questions must be answerable from the supplied training evidence; the model is instructed to refuse unrelated requests even when they contain a fitness keyword. This lexical gate is intentionally simple and may reject borderline questions. It is not a complete semantic classifier. Regardless of wording, Qwen has no command-execution tools or ability to modify the evidence corpus; saving workout proposals requires explicit approval.
