if [ -f /home/vagrant/.pygears/tools/tools.sh ]; then
    source /home/vagrant/.pygears/tools/tools.sh
fi

cd ~/pygears
git checkout develop
git pull

nosetests -w ~/pygears/tests

exit $?
