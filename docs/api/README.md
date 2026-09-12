# API

OpenAPI `/docs`. Auth: login, refresh, logout, me; client sends bearer token and `X-Organization-ID` for tenant endpoints. Errors carry `code`, `message`, `details`, `request_id`; pagination uses `page` and `page_size` (max 100). `POST /api/v1/bootstrap` is a privileged server-side provisioning route guarded by `X-Bootstrap-Key` and throttling. `POST /api/v1/users` is a basic provisioning flow; replace temporary-password transfer with invitation links before public onboarding.
