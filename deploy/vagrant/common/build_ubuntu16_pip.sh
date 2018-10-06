#!/usr/bin/env bash

sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.6 git

sudo ln -fs /usr/bin/python3.6 /usr/bin/python3

curl https://bootstrap.pypa.io/get-pip.py | sudo python3.6

sudo pip3 install -U --pre pygears
