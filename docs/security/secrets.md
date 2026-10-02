# Secrets

Use `.env` locally and a secrets manager in deployment. Rotate bootstrap and signing secrets according to operations policy. Never commit real secrets. BFF cookies are HttpOnly; API tokens are bearer credentials. Restrict `/bootstrap` at the network edge and remove or rotate its key after provisioning. Redis must be private. Avoid literal passwords in shell history.
