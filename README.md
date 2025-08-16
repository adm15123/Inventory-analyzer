# Inventory Analyzer

## Required Environment Variables

The application requires the following environment variables to be set:

- `SECRET_KEY`: Secret key used by Flask for session management.
- `MAIL_USERNAME`: Username for the SMTP server used to send emails.
- `MAIL_PASSWORD`: Password or app-specific password for the SMTP server.

Ensure these variables are defined in your environment before running the application.
Optional settings such as `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, and `MAIL_DEFAULT_SENDER`
may also be configured with environment variables if needed.
