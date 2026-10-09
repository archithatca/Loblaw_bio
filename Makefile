.PHONY: setup pipeline dashboard verify clean

PYTHON ?= python3

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) pipeline.py

dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

verify:
	$(PYTHON) verify_db.py

clean:
	rm -rf loblaw_bio.db outputs
