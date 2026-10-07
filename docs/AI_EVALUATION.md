# Local AI evaluation and limitations

The default model is `qwen3:4b-instruct-2507-q4_K_M`, running locally through Ollama. Existing explicit `OLLAMA_MODEL` settings are preserved; rerun SETUP_AI.cmd to select the new default. Model weights are downloaded separately, not included in the Windows ZIP.

## Why the model and guards changed

Real CPU tests of Qwen3 1.7B exposed English explanations, confusion between four years and four months of training, incorrect absolute-load arithmetic and unbalanced whole-body blocks. Earlier report acceptance covered structural checks only and must not be read as evidence of coaching quality.

The revised app supplies profile units explicitly, rejects predominantly non-Cyrillic generated prose, and requires each whole-body block session to contain lower-body, push and pull movements, with at most two exercises from one movement group. These constraints define this product's whole-body feature; they are not a hardcoded workout or a claim of scientific optimality. The model still selects exercises, sets, repetitions, RIR and progression notes.

The model selects a relative load fraction. Python computes loads from an exercise-specific recent reference, applies conservative limits and rounds down to the configured plate increment. No reference means no invented kilograms. An approved block that cannot fit the available time is rejected before inference.

## Reproduce

Install the model using SETUP_AI.cmd, start Ollama, then run EVALUATE_AI.cmd. The six scenarios use synthetic athletes only. The block scenario tests both generation and the first session after approval. Reports preserve the model name, corpus hash, timings and outputs. Older reports are retained to show failures transparently.

Application acceptance is a guard result, not proof of source entailment or appropriate individual training. The language guard checks script proportions, not Ukrainian fluency. The small curated evidence corpus is retrieval context, not model fine-tuning. Exact loads and personal outcomes are not established by group studies. Review each proposal before approving it.

The evidence file retains original English summaries and limitations alongside Ukrainian translations. Only the Ukrainian evidence text, ID and original source title enter coaching prompts. The corpus hash records this change. The general uncertainty notice is an application disclosure, so the model cannot truncate or replace it with an invented guarantee.
