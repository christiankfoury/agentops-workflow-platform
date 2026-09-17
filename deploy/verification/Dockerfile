ARG API_IMAGE=agentops-api:production
FROM ${API_IMAGE}
COPY oidc.py /app/oidc.py
ENTRYPOINT ["/usr/bin/tini", "-s", "--", "python", "oidc.py"]
