#!/usr/bin/env bash

sudo apt update
sudo apt install -y python3-pip
sudo pip3 install pygears-tools

pygears-tools-install -l pyenv python pygears verilator > /home/vagrant/dependencies.sh
yes | source /home/vagrant/dependencies.sh

pygears-tools-install pyenv python pygears verilator

source ~/.pygears/tools/tools.sh

cd ~
git clone https://github.com/bogdanvuk/pygears.git
