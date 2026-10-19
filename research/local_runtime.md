# Local runtime and isolated browser ports

The launcher uses API port `8000` and web port `5173` by default. It checks both
ports before starting and leaves existing listeners untouched. When another
session owns those ports, choose two explicit unused ports:

```bash
URBANSAARTHI_API_PORT=18710 URBANSAARTHI_WEB_PORT=15174 bash start-local.sh
```

For that example the app is `http://localhost:15174` and API documentation is
`http://localhost:18710/docs`. Logs are under `.runtime/local/18710-15174/`.
The launcher sets Vite's `NAGARSEVA_API_TARGET` to the chosen API port and checks
both API health and the web-to-API proxy before printing its ready URLs. Ports
must be distinct integers from 1 through 65535; occupied or invalid choices fail
without stopping another service. Ctrl+C stops only the API and Vite processes
created by this launcher.

The retained synthetic browser workflow also supports explicit isolated ports:

```bash
CHROMIUM_PATH=/usr/bin/chromium \
URBANSAARTHI_TEST_API_PORT=18700 \
URBANSAARTHI_TEST_WEB_PORT=14174 \
nagarseva/.venv/bin/python nagarseva/tests/check_urban_browser.py
```

Its defaults remain `8000` and `4173`. The check starts its own disposable SQLite
API and Vite preview, records the chosen ports, and stops only its owned servers.
Without `CHROMIUM_PATH` it uses the Chromium installed by Playwright. Build the
frontend first when its source has changed. Synthetic workflow records and browser
screenshots do not establish field performance or government verification.
