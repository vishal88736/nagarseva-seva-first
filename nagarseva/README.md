# UrbanSaarthi application

The default frontend now follows the focused five-screen UrbanSaarthi brief. See the [root run guide](../README.md) and [architecture and validation notes](docs/urbansaarthi.md).

Use `make urban-setup PYTHON=python3.12`, then `make api PYTHON=python3.12` and, in another terminal, `make web`. A dedicated virtual environment is recommended. `make test` runs the focused API/calculation tests, browser-engine tests and build. Full legacy model checks require `make setup` and `make test-legacy`.

The recommended API is `model.api.urban:app`. The original model-backed API remains available through `make legacy-api`; its `/urban` routes also support the new interface. The [historical NagarSeva guide](README.NagarSeva.md) describes the earlier broader interface; its default `make api` command now starts the focused app.

No synthetic data or model retraining is required to start UrbanSaarthi. Five cluster geometries and indicators are explicit demonstration fixtures. Real SRA listing records are shown separately, without invented coordinates or service status. Physical completion never automatically verifies a service.
