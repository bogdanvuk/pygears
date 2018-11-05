if [ -f /home/vagrant/.pygears/tools/tools.sh ]; then
    source /home/vagrant/.pygears/tools/tools.sh
fi

cd ~/pygears
git checkout develop
git pull

pytest ~/pygears/tests

exit $?
