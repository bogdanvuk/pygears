#!/usr/bin/env bash

sudo zypper --non-interactive update
sudo zypper --non-interactive install python3-pip git
sudo pip3 install -U --pre pygears pytest

sudo zypper --non-interactive install gcc gcc-c++
