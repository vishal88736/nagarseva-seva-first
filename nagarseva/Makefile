PYTHON ?= python

.PHONY: setup data train api web all test docs clean

setup:
	$(PYTHON) -m pip install -r model/requirements.txt
	npm --prefix website install

data:
	$(PYTHON) model/src/generate_data.py
	$(PYTHON) model/src/data_quality.py

train: data
	$(PYTHON) model/src/train_priority.py
	$(PYTHON) model/src/train_service_gap.py
	$(PYTHON) model/src/train_cost.py
	$(PYTHON) model/src/train_grievance_nlp.py

api:
	$(PYTHON) -m uvicorn model.api.main:app --host 0.0.0.0 --port 8000 --reload

web:
	npm --prefix website run dev

# Builds the complete local demo, then starts API and Vite in the background.
# Use `make api` / `make web` when foreground logs are preferred.
all: setup train
	@nohup $(PYTHON) -m uvicorn model.api.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 & echo "API started on http://localhost:8000"
	@nohup npm --prefix website run dev > web.log 2>&1 & echo "Web started on http://localhost:5173"

test:
	$(PYTHON) -m pytest model/tests -q
	npm --prefix website run build

docs:
	$(PYTHON) docs/build_documentation.py

clean:
	rm -rf website/dist website/node_modules
