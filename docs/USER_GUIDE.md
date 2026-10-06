# User guide

## Recording a workout

Send `Жим лежачи 3x10 60 кг` to save three sets of ten reps at 60 kg. `Присідання 8 80 кг` saves one set of eight reps at 80 kg. Use `0 кг` for exercises without added weight. One quick message records one exercise.

For sets with different weights, use **💪 Почати тренування → 💪 Силові вправи → exercise**, then send:

```text
60 10
62,5 8
65 6
```

Each line is **weight in kg, then repetitions**. Press **💾 Зберегти вправу**. Invalid batches are rejected without partially adding their valid lines. Before saving, the sets are only a temporary draft; a restart loses that draft. Saved sets survive restarts. Use **🏁 Завершити тренування → ✅ Підтвердити завершення** to close the session.

Keep exercise names consistent. Capitalization is ignored for history/chart lookup, but synonyms are not merged. For dumbbells, consistently choose either weight per dumbbell or combined weight. Editing a Telegram message does not edit the stored entry. Delete the exercise record by its history ID and add it again.

## History and charts

`/history` shows five recent workouts with every saved set, including active workouts. `/history 2` shows the next page. `/exercise Жим лежачи` shows the last five workouts containing that exercise. Each exercise entry has a stable ID for `/delete ID`.

Charts use rolling 7, 30, 90 or 365-day windows, including today. These are not calendar months, quarters or years. The overview shows daily sets and recorded volume. An exercise chart shows its daily maximum weight, repetitions and volume. Volume is **weight × reps**, added across sets; it is a logging metric, not an assessment of health or training quality. Zero-load exercises have zero recorded volume; reps still count.

Dates use the PC's local time at recording. Backdating is not supported in this version. If you send a message while the bot is off, it is processed at the next startup; Telegram retains pending updates for at most 24 hours. Do not rely on offline messages as a durable log.

## Body measurements

Use semicolons to separate measurements:

```text
/measure біцепс лівий 35,5 см; біцепс правий 36 см; талія 82 см; вага 80 кг
```

Use `см` for circumferences and `вага … кг` for body weight. The menu **📏 Мої виміри** shows the ten latest measurement records and their IDs. `/measure_delete ID` deletes one record. `/graph 365 біцепс лівий` plots that measurement. If multiple measurements fall on the same date, the latest recorded one is plotted.

## Reminders

`/remind 10` enables one daily summary of exercises not recorded for at least ten days. It runs after 18:00 in the PC's local time. `/remind 0` disables it. Only exercises already in the diary can appear. A late startup catches up today's reminder; missed days are not sent individually. A network failure immediately after delivery can cause a duplicate message.

## Export, backup and migration

The export menu creates CSV or Excel reports of **completed workouts**, either for the current calendar month or all recorded history up to the implementation's 5,000-workout limit. Excel includes a summary, workout list and individual sets. Standalone measurement records are not included in these reports.

For a full backup, stop the app and copy `data/nextset.sqlite3`. Copying the entire `data/` folder also preserves the token and pairing; treat it as private. A fresh install intentionally contains no credentials or personal records. To switch computers, stop the old app before starting the new one with the same token.

## Optional AI

Install Ollama and `qwen3:1.7b` separately. Send one exercise per `/ai` request. Review the proposed Ukrainian name, weight and reps; `/confirm` saves it and `/cancel` discards it. Output is validated, but valid-looking values can still be wrong. The model cannot run commands or access the database directly. This is text extraction, not an autonomous fitness coach.

## Starting with Windows

Autostart is not enabled by default. If desired, create a shortcut to `NextSet.exe`, press **Win+R**, enter `shell:startup`, and put the shortcut there. This starts the app when you sign in, not while the PC is asleep or shut down. Complete the first-time setup manually before adding the shortcut.
