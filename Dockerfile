FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/jorsonbei/property-state-model"
LABEL org.opencontainers.image.description="Property-State Model local chat alpha"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/outputs/psm_v0 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434

WORKDIR /app

RUN useradd --create-home --uid 10001 psm

COPY --chown=psm:psm outputs/psm_v0/psm_v0 /app/outputs/psm_v0/psm_v0
COPY --chown=psm:psm outputs/psm_v0/product_alpha_app /app/outputs/psm_v0/product_alpha_app
COPY --chown=psm:psm outputs/psm_v0/runtime /app/outputs/psm_v0/runtime
COPY --chown=psm:psm outputs/psm_v0/V0_262_INVITE_ONLY_TRIAL_NOTICE.md /app/outputs/psm_v0/V0_262_INVITE_ONLY_TRIAL_NOTICE.md

USER psm
EXPOSE 8765

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/status', timeout=2)" || exit 1

CMD ["python", "outputs/psm_v0/product_alpha_app/server.py", "--host", "0.0.0.0", "--port", "8765"]
