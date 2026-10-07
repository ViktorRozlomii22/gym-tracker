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

Whole-body block JSON requires lower-body, push and pull slots, followed by optional accessory slots. The exercise within each slot and all numeric ranges remain model decisions. App validation additionally rejects duplicate exercises and excessive per-movement duplication. This generation constraint was added after a real model still produced an unbalanced block despite correct prompt instructions.

## Grounded display

Real outputs still included unsupported interpretations such as treating high RIR as a hypertrophy advantage. The app therefore replaces generated plan rationales and exercise explanations with truthful product notices and reference/calibration facts. Conceptual Q&A displays the selected reviewed source summaries and their limitations directly, rather than trusting a small model to paraphrase scientific conclusions. Numeric workout choices remain model-generated and experimental; this does not prove their individual optimality. Weekly AI interpretation and progression notes also require human review.

Accessory selection now uses a map keyed by exercise ID rather than an array. This prevents the repeated-ID failure observed in a real test. The lower-body, push and pull objects have disjoint ID sets; optional accessories remain model choices (maximum three). Existing approved blocks keep their canonical item-list representation.

## Recorded runs on 7 October 2026

| Configuration | Cases accepted by app guards | What it showed |
| --- | --- | --- |
| 4B Instruct, initial English evidence | 5/6 | Refused a calibration-only substitution; prose also needed review. |
| Ukrainian evidence, array blocks | 5/6 | The block was rejected as unbalanced. |
| Required movement slots, array accessories | 5/6 | The block was rejected for a repeated exercise identity. |
| Unique accessory map and grounded display, targeted retest | 2/2 | Full four-week block plus first session, and extractive evidence Q&A passed. |

The final targeted report is [qwen-20261007-094638.json](evaluation/qwen-20261007-094638.json). The preceding six-case report is [qwen-20261007-093115.json](evaluation/qwen-20261007-093115.json). These are distinct runs, not a claimed 6/6 final full-suite score. Remaining numeric choices and weekly AI advice are experimental and require review.

During CPU evaluation, Ollama reported 3,884,460,276 bytes (about 3.62 GiB) of model allocation at an 8192-token context and zero GPU allocation. This excludes other process/system memory. The download is about 2.5 GB. On this CPU, generation was roughly 6–8 tokens/second; large blocks take several minutes. The isolated evaluation server was stopped after each run. No live Telegram bot was started.
