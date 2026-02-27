.PHONY: install run extract-pst extract-eml export-neo4j test clean

install:
	pip install -e ".[dev]"

run:
	python main.py

extract-pst:
	python extract_pst_to_json.py

extract-eml:
	python extract_eml_folder.py

export-neo4j:
	python graph_to_neo4j.py

test:
	python -m pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name "*.egg-info" -exec rm -r {} +
