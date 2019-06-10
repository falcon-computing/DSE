env:
	virtualenv -p python3 venv
	venv/bin/pip3 install -r dev_reqs.txt

lint:
	python3 -m pylint autodse --rcfile=tests/lint/pylintrc

type:
	mypy autodse --ignore-missing-imports

tox:
	tox

unit_test:
	pytest --lf

example:
	rm -f *.log
	python3 -m autodse --src-dir=./examples/kmeans --work-dir=./work \
					  --config=./examples/kmeans/dse_config.json \
					  --db=./work/result.db

format:
	yapf -ir --style=tests/lint/yapf_style.cfg autodse
	yapf -ir --style=tests/lint/yapf_style.cfg tests

cov:
	pytest --cov=autodse --cov-report term

doc:
	make -C docs clean html

clean:
	rm -rf .coverage *.xml *.log *.pyc *.tox *.egg-info tests/temp* tests/*.pdf
