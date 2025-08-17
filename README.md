# Inventory Analyzer

## Environment Variables

The application looks for the following environment variables.  All are
optional and have reasonable defaults for local development, but you
should provide real values in production:

- `SECRET_KEY`: Secret key used by Flask for session management.
- `MAIL_USERNAME`: Username for the SMTP server used to send emails.
- `MAIL_PASSWORD`: Password or app-specific password for the SMTP server.

Additional settings such as `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`,
and `MAIL_DEFAULT_SENDER` may also be configured with environment
variables if needed.
