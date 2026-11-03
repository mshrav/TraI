# Security notes

- The source archive supplied for this cleanup contained an active-looking Telegram bot token and real Telegram user profile records. Those files and records are not present in this cleaned package.
- Revoke the previously exposed Telegram token in `@BotFather` and generate a new one before testing. Removing a secret from the latest source snapshot does not invalidate the old token.
- If secrets or personal data were pushed to the original Git repository, rotate/revoke secrets and purge sensitive files from Git history. Deleting them in a later commit is not sufficient.
- Keep `.env`, `bot_config.json`, `user_data.json`, and `messages.json` out of Git. The `.gitignore` file already excludes them for future commits.
- The local admin dashboard has no login. Keep `DASHBOARD_HOST=127.0.0.1`; do not expose port 5000 to a public network.
- The webhook can be protected with `DASHBOARD_WEBHOOK_TOKEN`. The Telegram process sends the same value in `X-TraI-Webhook-Token`.
- Do not use real customer details in demos. Use synthetic test users.
