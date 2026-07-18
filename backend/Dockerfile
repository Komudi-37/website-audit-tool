FROM python:3.11-slim

# Install Node.js (needed for `npx lighthouse` in performance.py)
# and a real system Chromium browser that Lighthouse's chrome-launcher can find.
# (This is separate from Playwright's own browser install below — Lighthouse
# does not use Playwright's browser, it needs its own system Chrome/Chromium.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates chromium \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Tell Lighthouse exactly where that Chromium binary is, so it doesn't
# have to guess/auto-detect (which can be unreliable in containers).
ENV CHROME_PATH=/usr/bin/chromium

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install lighthouse globally so npx finds it instantly at runtime
# (avoids a slow/unreliable on-demand download during the demo)
RUN npm install -g lighthouse

# Playwright browser + all its OS-level dependencies, baked into the image
RUN playwright install --with-deps chromium

# App code
COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]