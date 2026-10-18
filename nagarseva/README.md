# UrbanSaarthi application

The default acquired-data workspace and its separate synthetic sandbox are described
in the [current run guide](../README.md), [source results](../research/data_availability.md)
and [API/storage guide](docs/public-data-api.md). `model.api.urban:app` serves both
namespaces. The legacy ML API retains its old `/urban` sandbox contract; the acquired
workspace requires the focused API. `make acquire-public-data` runs the public pipeline.

The default frontend now follows the focused five-screen UrbanSaarthi brief. See the [root run guide](../README.md) and [architecture and validation notes](docs/urbansaarthi.md).

Use `make urban-setup PYTHON=python3.12`, then `make api PYTHON=python3.12` and, in another terminal, `make web`. A dedicated virtual environment is recommended. `make test` runs the focused API/calculation tests, browser-engine tests and build. Full legacy model checks require `make setup` and `make test-legacy`.

The recommended API is `model.api.urban:app`. The original model-backed API remains available through `make legacy-api`; its `/urban` routes also support the new interface. The [historical NagarSeva guide](README.NagarSeva.md) describes the earlier broader interface; its default `make api` command now starts the focused app.

No model retraining is required. Acquired mode loads verified source files, retaining
missing service measurements; the separate five-cluster sandbox uses synthetic
fixtures. Physical completion never automatically verifies a service.
