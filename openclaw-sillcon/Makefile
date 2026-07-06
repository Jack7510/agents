.PHONY: test lint

test:
	python3 -m unittest discover -s tests

lint:
	PYTHONPYCACHEPREFIX=.pycache python3 -m compileall scripts tests
