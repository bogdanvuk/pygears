#!/usr/bin/env bash

sudo zypper --non-interactive update
sudo zypper --non-interactive install python3-pip git
pip3 install -U --pre pygears
