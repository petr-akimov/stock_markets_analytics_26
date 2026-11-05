PYTHON = python
PIP = pip

setup:
	pip install -r requirements.txt

ingest:
	$(PYTHON) -m src.data.ingest

features:
	$(PYTHON) -m src.features.build_features

train:
	$(PYTHON) -m src.models.train

signals:
	$(PYTHON) -m src.strategy.generate_signals

backtest:
	$(PYTHON) -m src.backtest.simulator

run_all: ingest features train signals backtest