# Choosing a training method

Open **More → All methods** or `/programs`. Choose a goal, read one Ukrainian card, then explicitly confirm a selection. Browsing never changes a plan. Changing a method archives the accepted block and clears proposals; actual workouts and PRs remain.

Each card contains its focus, intended audience, practical advantages and disadvantages, three-day arrangement, progression principle, limitations and source links. These are ten options, not a scientific ranking for natural lifters. Years of training alone do not determine training level.

| ID | Orientation | Main trade-off |
|---|---|---|
| `hypertrophy` | SBS-inspired hypertrophy | Performance feedback and flexible scheduling; demanding final sets need fatigue management |
| `madcow` | Madcow-inspired strength | Clear heavy/light/medium rhythm; fixed weekly increases can outpace recovery |
| `531` | 5/3/1-inspired strength | Patient submaximal progression; depends on a sensible training maximum |
| `bridge` | Bridge-inspired transition | Effort-based load selection; aimed at transition from novice progression, not every advanced athlete |
| `fullbody` | Andy Baker-inspired hypertrophy | Compact whole-body structure and double progression; working-set quality matters |
| `dup` | Daily undulating periodization | Different rep emphases across days; comparisons require matching corresponding sessions |
| `linear` | Linear periodization | Clear direction across weeks; missed sessions need recalibration |
| `double` | Double progression | Reps first, load second; large equipment increments can disrupt progress |
| `autoregul` | RIR autoregulation | Responds to day-to-day readiness; subjective effort estimates can be inaccurate |
| `minimal` | Time-constrained moderate volume | Easier scheduling; may sacrifice hypertrophy volume |

The first five are author-inspired adaptations, not the original spreadsheets or paid templates. The remaining five are generic principles that overlap: a full-body routine can use both double progression and RIR. Selecting an orientation supplies a compact philosophy to Qwen; it does not load hardcoded workout prescriptions. The current block format remains three recurring whole-body sessions.

Author descriptions establish what an original program contains. Research summaries establish broader findings about resistance training; they do not validate any particular bot-generated plan. Card pros/cons are explicitly labelled editorial practical assessments. The original SBS template spans 21 weeks; an eight-week bot adaptation is not that original program. Three-day adaptations of 5/3/1 are distinguished from author variants with other frequencies.

Primary references are linked in every card in `knowledge/programs.json`. The local RAG corpus adds the [2022 volume-equated periodization review](https://pubmed.ncbi.nlm.nih.gov/35044672/) and [2017 linear-versus-DUP hypertrophy review](https://pmc.ncbi.nlm.nih.gov/articles/PMC5571788/). Results differ by outcome and population; there is no universal winner. Catalogue review: 2026-10-19.

To add a method, add a unique entry to `knowledge/programs.json` with the same fields, evidence caveats and verified sources. Preserve existing IDs because saved user profiles reference them. Add a short English `description` for the small model and Ukrainian presentation fields. Do not send the entire catalogue to the model. Run the catalogue and generation regression tests before publishing.
