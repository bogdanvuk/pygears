source /home/vagrant/.pygears/tools/tools.sh

pip install nose
nosetest -w ~/pygears/tests

echo $? > /vagrant/test.res
