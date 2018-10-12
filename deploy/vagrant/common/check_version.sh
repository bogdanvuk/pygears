if [ -f /home/vagrant/.pygears/tools/tools.sh ]; then
    source /home/vagrant/.pygears/tools/tools.sh
fi

python3 -c "import pygears; import sys; sys.exit(pygears.__version__ != \"$PYGEARS_VERSION\")"

exit $?
