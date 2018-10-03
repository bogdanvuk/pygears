rm -rf dist build
python3 setup.py sdist
twine upload dist/*
