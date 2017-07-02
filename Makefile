.PHONY: release

release:
	tox
	python setup.py sdist bdist_wheel
