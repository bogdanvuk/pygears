source /home/vagrant/.pygears/tools/tools.sh

cd ~/pygears
git checkout develop
git pull

pip3 install nose
nosetests -w ~/pygears/tests

exit $?
