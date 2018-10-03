source /home/vagrant/.pygears/tools/tools.sh

python -c "import pygears; import sys; sys.exit(pygears.__version__ != \"0.1.1-dev0\")"

exit $?
