env:
	virtualenv -p python3 venv
	venv/bin/pip3 install -r dev_reqs.txt

lint:
	python3 -m pylint autodse --rcfile=tests/lint/pylintrc
	mypy autodse/

tox:
	tox

unit_test:
	pytest

example:
	rm -f *.log
	python -m autodse --src-dir=./examples/kmeans --work-dir=./work \
					  --config=./examples/kmeans/dse_config.json

format:
	yapf -ir --style=tests/lint/yapf_style.cfg autodse
	yapf -ir --style=tests/lint/yapf_style.cfg tests

cov:
	pytest --cov=autodse --cov-config=tests/lint/coveragerc

doc:
	make -C docs clean html

clean:
	rm -rf .coverage *.xml *.log *.pyc *.tox *.egg-info tests/temp*
