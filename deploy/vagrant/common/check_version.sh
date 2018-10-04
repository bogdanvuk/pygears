source /home/vagrant/.pygears/tools/tools.sh

python -c "import pygears; import sys; sys.exit(pygears.__version__ != $PYGEARS_VERSION)"

exit $?
