packages: sdist wheel2 wheel3 clean

sdist:
	python setup.py sdist

wheel2:
	python2 setup.py bdist_wheel

wheel3:
	python3 setup.py bdist_wheel

clean:
	rm -rf .cache .eggs build *.egg-info
	find {{ cookiecutter.project_slug }} -type d -name __pycache__ -exec rm -rf {} \;
