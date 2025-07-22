# Makefile

.PHONY: install run export clean

install:
	pip install -e .

run:
	python main.py

extract-pst:
	python extract_pst_to_json.py

extract-eml:
	python extract_eml_folder.py

export-neo4j:
	python graph_to_neo4j.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
