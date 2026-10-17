FROM node:24-bookworm-slim AS frontend
WORKDIR /source/nagarseva/website
COPY nagarseva/website/package.json nagarseva/website/package-lock.json ./
RUN npm ci
COPY nagarseva/website/ ./
COPY nagarseva/shared/ ../shared/
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    NAGARSEVA_MODE=hosted-demo URBANSAARTHI_DB_PATH=/data/urbansaarthi.sqlite3
WORKDIR /app
COPY nagarseva/model/requirements-urban.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && groupadd --gid 10001 urban && useradd --uid 10001 --gid urban --no-create-home urban \
    && mkdir /data && chown urban:urban /data
COPY nagarseva/model/api/urban.py nagarseva/model/api/store.py ./model/api/
COPY nagarseva/model/src/urban_planning.py ./model/src/
COPY nagarseva/shared/ ./shared/
COPY deploy/aws/app.py ./hosted.py
COPY --from=frontend /source/nagarseva/website/dist/ ./frontend/
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8080/api/urban/health',headers={'X-Origin-Verify':os.environ['URBANSAARTHI_ORIGIN_SECRET']}); urllib.request.urlopen(r,timeout=4)"
CMD ["python", "-m", "uvicorn", "hosted:build_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-proxy-headers"]
