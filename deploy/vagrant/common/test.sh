source /home/vagrant/.pygears/tools/tools.sh

pip3 install nose
nosetests -w ~/pygears/tests

exit $?
