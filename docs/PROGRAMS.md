# Adaptive training plans

Open `/programs` in Telegram or press **🧭 Програми**. All bot messages remain Ukrainian. These five options are **NextSet adaptations inspired by published programs**, not official implementations, endorsements, or a scientifically ranked “top five for natural lifters.” No drug use is assumed or required. The current templates are for adults with access to a barbell gym and cable machines.

| Bot option | Published reference | Focus |
|---|---|---|
| `hypertrophy` | [SBS Hypertrophy](https://www.strongerbyscience.com/program-bundle/) | Muscle growth, performance feedback |
| `madcow` | [Madcow 5×5](https://stronglifts.com/madcow-5x5/) | Strength, heavy/light/medium structure |
| `531` | [5/3/1 Full Body](https://www.jimwendler.com/blogs/jimwendler-com/5-3-1-beach-body-performance-based-challenge) | Long-term submaximal strength waves |
| `bridge` | [The Bridge](https://www.barbellmedicine.com/the-bridge-2/) | Strength with effort-based adaptation |
| `fullbody` | [Andy Baker Full Body Hypertrophy](https://www.andybaker.com/programs/full-body-hypertrophy/) | Compact whole-body hypertrophy |

These references are for experienced trainees, including someone with four years of training. They are not an evidence-based ranking of branded programs. No original paid program is bundled. There are **no stored workout templates**: Qwen creates the next session from the selected philosophy, retrieved research summaries, profile, recent PRs, completed workouts, effort feedback, measurements and missed-session notes.

## Setup in Telegram

1. Run `SETUP_AI.cmd` once. Install Ollama and download the model if needed. The diary works without AI, but AI coaching requires a running local model.
2. Select an orientation: `/program hypertrophy` (other IDs are in the table above).
3. Enter `/profile вік 30; зріст 180; вага 80; досвід 4; крок 2,5; мета м’язи; обладнання зал`. Replace values with your own. Age and experience are years, height cm, weight and available increment kg. Goals: `сила`, `м’язи`, `загальна`. Current exercise catalog requires a barbell gym and machines/cables.
4. Add measurements with `/measure`, then actual recent performances with `/pr Жим лежачи; 60; 8; 2026-10-06`. Replace the date. Enter 1–10 repetitions and the weight of an already completed set; no special maximum attempt is necessary.
5. Optionally request `/block 4` (4–6 weeks), review and `/blockconfirm`, then `/checkin` before training. `/plan` retrieves evidence and asks local Qwen for a proposed session. The request allows up to six minutes; actual speed depends on CPU and history size. It shows exercises, weights, sets, reps, RIR, reasoning, uncertainty and source links. Inspect the proposal. `/planconfirm` accepts; `/planreject` discards. Repeated previews return the same saved proposal that day. See [TRAINING_GUIDE.md](TRAINING_GUIDE.md) for stable blocks, substitutions, exercise feedback, weekly reports and recovery.
6. Warm up and adjust downward if needed. Barbell weights include the bar; dumbbell weights mean one dumbbell. Log actual sets normally. `/done 3` records your lowest estimated repetitions in reserve (RIR) across the session and advances the sequence once. A plan is never recorded as performed merely because it was generated or accepted. Partial sessions preserve actual work, not imagined successful sets.

## Evidence-grounded generation, not fine-tuning

`knowledge/evidence.json` contains seven short, independently written source summaries. Each includes its original link, study type, population and limitations. It covers resistance training prescription, volume, proximity to failure, autoregulation and general illness guidance. The initial curated review date is October 6, 2026. It is a small starting corpus, not a comprehensive literature review or full-text research database.

`coach_rag.py` retrieves up to four relevant cards through bilingual lexical search and supplies them to Qwen with a compact athlete history. No separate embedding model, vector server, cloud API or live web search is required. `/ask Чому не треба кожен підхід до відмови?` answers questions from retrieved cards. `/sources` lists the evidence base. Unsupported queries are refused when retrieval finds no match or the model reports insufficient evidence.

This is **retrieval-augmented generation (RAG)**. Model weights are not trained or fine-tuned. Personal history is supplied as context; the system does not secretly retrain itself. Source IDs are checked against the retrieved records and links are rendered from the trusted catalog. This checks citation identity, **not whether every generated claim is logically supported**. A small model can still misinterpret a study or produce a poor plan with real citations. The corpus contains differing evidence rather than treating a single study as settled truth.

The model chooses exercises, reps, sets, RIR and a relative load fraction. The app calculates kilograms from that fraction, your fresh strength reference, the conservative ceiling and your plate increment. This keeps arithmetic out of the small language model. There is no fixed progression increment or hardcoded branded workout. The original programs are reading references, not purported exact implementations. No source proves an exact kilogram prescription for an individual.

## Validation and health constraints

The remaining programmed rules are transparent app safeguards, not claims of scientifically optimal training:

- Adults only in this version. Known exercise IDs; finite positive weights; 1–5 sets per exercise; 3–20 reps; RIR 1–5; at most six exercises and 24 work sets per ordinary session.
- A fresh PR (up to 90 days) or a recent recorded performance is required for numeric kilograms. Otherwise the model must request light warm-up calibration using `kg: null`.
- A repetition-based strength reference uses the Epley approximation. Suggested kilograms cannot exceed `reference / (1 + (reps + RIR) / 30)`, and are rounded down to the selected increment. This is an approximate plausibility check, not proof of safety or a target weight.
- `/status хворію` or `/status біль` pauses plan generation and exercise reminders. “Feeling good” cannot override the pause. `/status одужав` explicitly reports recovery after illness; `/status дозволено` reports professional assessment after pain. The bot cannot verify clearance.
- Return mode lasts three confirmed sessions, or is triggered after a gap of 14 days. Return and bonus sessions are capped at eight total sets, two sets per exercise, RIR at least 3 and 80% of the ordinary validation ceiling. These are deliberately cautious software limits; the model may suggest less. They are not a universal rehabilitation prescription.
- `/status втома` passes fatigue to Qwen and lowers the validation ceiling. `/skip робота` records a missed session without advancing the sequence. The model receives missed-session notes and elapsed time.
- At least 48 hours separate completed coach sessions. No more than three main and four total sessions in a rolling seven days. `/extra` requires three completed main sessions with reported RIR at least 3, today's `/status добре`, and no return block. Qwen chooses the light extra session; it does not advance the main sequence.

Do not train with fever or significant systemic illness. Stop and seek medical assessment for chest pain, unusual breathlessness or fainting. The bot cannot diagnose or decide that you are medically fit. [Mayo Clinic exercise and illness guidance](https://www.mayoclinic.org/healthy-lifestyle/fitness/expert-answers/exercise/faq-20058494).

## Free-text updates and storage

`/coach` extracts one event from a Ukrainian sentence (skip, illness, pain, fatigue, recovery, feeling good, next plan or extra day). Review the proposed command before `/coachconfirm`; `/cancel` discards it. Explicit profile/PR commands avoid ambiguous dates and units. Neither a parsed message nor an AI answer writes a workout directly.

Plans, approvals, actual sets, RIR, source snapshots, corpus hash and model name are stored in SQLite. Only the last six completed coach sessions, recent measurements and five skip notes enter the prompt. Older ordinary diary entries not completed through `/done` are not automatically interpreted as adherence; enter current PRs when onboarding. Back up `data`. Deleting all diary data also deletes the coach state. All inference requests go to the fixed loopback address `127.0.0.1:11434`; normal Telegram communication still requires internet.

## Updating and evaluating

Add or amend independently written cards in `knowledge/evidence.json`; include an original source URL, population, study type, limitations and bilingual search tags. Update the version and review date. Source installations read this file on the next request; EXE distributions need rebuilding. Do not paste unreviewed web instructions or claim automatic evidence updates.

The default remains Qwen3 1.7B, with an 8192-token context for coaching and immediate model unloading after responses. Hardware suitability and actual response time must be checked on the target PC. Runtime model requests time out after 180 seconds; invalid/truncated outputs are rejected without replacing a plan. More capable models can be selected via `OLLAMA_MODEL`, but there is no guarantee this small model can reliably design high-quality training.

Automated unit tests use mocked model outputs to check retrieval, provenance identity, numeric constraints, approval, illness state, replay handling, block consistency, substitutions, actual-workout completion and backups. **They do not validate real Qwen coaching quality or scientific entailment.** No live Ollama or Telegram service is started during these tests. `EVALUATE_AI.cmd` separately exercises the real model on six synthetic cases and saves all results for manual review. Guard acceptance is not a scientific quality certificate. Coaching remains experimental.
