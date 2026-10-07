# Troubleshooting

| Problem | What to do |
| --- | --- |
| The app cannot write data | Extract the whole ZIP into a writable folder such as Documents. Do not run inside the ZIP or from Program Files. |
| Token validation fails | Check internet access and copy the complete token from BotFather. No token is saved after a failed validation. |
| The bot ignores messages | Open the exact pairing link printed at startup and press Start. Only the paired private account is allowed. |
| Nothing happens after restarting | Send `/start` in Telegram to reopen the menu. Stored exercises remain available. |
| Telegram reports a conflict | Stop the other copy using the same token. Only one polling process can run per token. |
| A graph is empty | Use the exact recorded exercise/measurement name and a period containing entries. |
| No reminders arrive | Enable `/remind 10`; keep PC awake, internet connected and app running after 18:00. |
| Local AI is unavailable | Start Ollama and run `ollama pull qwen3:4b-instruct-2507-q4_K_M`. Normal bot features do not require it. |
| Windows displays an unknown-publisher notice | The app is not code-signed. Verify its source and release checksum; alternatively build it yourself. Do not disable antivirus protections. |

## Change or revoke a token

Revoke a compromised token through BotFather. Stop NextSet, then run `NextSet.exe --setup` from its folder to replace the locally stored token. Source mode: `python launcher.py --setup`. Never paste tokens into GitHub issues, commits or screenshots.

## Diagnostics

`NextSet.exe --check` runs an offline check of SQLite, the input parser, chart rendering, Excel and application initialization without using your token. It does not test Telegram delivery. Source mode: `python launcher.py --check`.

The Windows HTTPS compatibility adapter retains Windows certificate validation. It is selected only when the normal Python TLS setup fails with a permissions error. No TLS verification is disabled.

## Release checksums

Compare the downloaded archive with `NextSet-UA-Windows.zip.sha256`:

```powershell
Get-FileHash .\NextSet-UA-Windows.zip -Algorithm SHA256
```

## Security and privacy

Only the paired Telegram account can use the bot in a private chat. Local files are not separately encrypted. Telegram processes the chat messages, exports and chart images. Optional AI requests remain on localhost. Share bug reports without your `data/` folder, token, real measurements or workout history.
