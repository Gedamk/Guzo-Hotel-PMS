# Security Notes

This project should not commit real credentials, production secrets, API keys, database passwords, service account JSON files, or private tokens.

## Credential Rules

- Keep real values in `.env`, local credential files, deployment secrets, or a managed secret store.
- Keep `.env` local-only and ignored by git.
- Use `.env.example` only for safe sample variable names and placeholder values.
- Do not commit real Google service account JSON files.
- Do not commit real SendGrid, Twilio, Stripe, Chapa, Telegram, OpenAI, database, or email credentials.
- Do not commit `GUZO_SMTP_PASSWORD`, `GUZO_SMTP_USERNAME`, `GUZO_EMAIL_FROM`, or provider-specific email credentials.
- Do not place production secrets in README files, docs, screenshots, logs, generated reports, or test fixtures.

## Local Credential Files

If a local file is needed for development, use a path that is ignored by git and document the expected environment variable in `.env.example`.

Example pattern:

```env
GOOGLE_APPLICATION_CREDENTIALS=local/path/to/service-account.json
DATABASE_URL=postgresql://user:password@localhost:5432/guzo
```

The values above are examples only. Real project values should stay local or in deployment secrets.

## If A Secret Was Committed

If a real secret has already been committed:

1. Rotate or revoke the exposed credential immediately.
2. Replace the committed value with a placeholder or remove the file from tracking.
3. Review git history cleanup separately.
4. Confirm `.gitignore` prevents the same type of secret from being added again.

## Refactor Reminder

Security cleanup should be handled separately from large folder refactors. Do not mix secret removal, app moves, dependency changes, and route rewrites in one pull request.
