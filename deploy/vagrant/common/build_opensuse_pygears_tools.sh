#!/usr/bin/env bash

sudo zypper --non-interactive update
sudo zypper --non-interactive install python3-pip git
sudo pip3 install --pre pygears-tools

pygears-tools-install -l pyenv python pygears verilator > /home/vagrant/dependencies.sh
source /home/vagrant/dependencies.sh

sudo zypper --non-interactive install gcc gcc-c++

pygears-tools-install pyenv python pygears verilator

source ~/.pygears/tools/tools.sh

pip install -U --pre pygears pytest
