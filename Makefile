env:
	virtualenv -p python3 venv
	venv/bin/pip3 install -r dev_reqs.txt

lint:
	python3 -m pylint autodse --rcfile=tests/lint/pylintrc
	mypy autodse/

unit_test:
	pytest

conv:
	#pytest --cov --cov-report=xml:cov.xml
	pytest --cov=autodse

doc:
	make -C docs clean html

clean:
	rm -rf .coverage *.xml *.log *.pyc
