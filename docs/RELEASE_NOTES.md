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
