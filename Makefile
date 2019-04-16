lint:
	python3 -m pylint autodse --rcfile=tests/lint/pylintrc
	mypy autodse/

unit_test:
	pytest

conv:
	pytest --cov --cov-report=xml:cov.xml

clean:
	rm -rf .coverage *.xml *.log *.pyc