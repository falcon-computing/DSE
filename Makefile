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

format:
	yapf -ir --style=tests/lint/yapf_style.cfg autodse

cov:
	pytest --cov=autodse --cov-config=tests/lint/coveragerc

doc:
	make -C docs clean html

clean:
	rm -rf .coverage *.xml *.log *.pyc *.db *.tox *.egg-info
