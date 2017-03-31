SHELL := /bin/bash

default: test dist

dist: venv-python3
	venv-python3/bin/python setup.py bdist_wheel --universal

venv-%:
	virtualenv -p $* $@
	$@/bin/pip install -r <(cat requirements.txt requirements-dev.txt)

lint-%: venv-%
	venv-$*/bin/flake8 logbeam

test-%: venv-%
	venv-$*/bin/py.test logbeam

test: lint-python3 test-python2 test-python3

clean:
	rm -rf build dist *.egg-info

clean-all: clean
	rm -rf venv-python2 venv-python3

tag: venv-python3
	git tag $(shell venv-python3/bin/python setup.py --version)

.PHONY: lint-% test-% test clean clean-all
