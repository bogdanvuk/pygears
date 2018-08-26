#!/usr/bin/env python3

import os
import sys
import logging
import json
import importlib.machinery
import shutil
import glob
import errno
from utils import (shell_source, custom_run, download_and_untar, clone_git,
                   install_deps, set_env)


def create_logger(pkg):
    logger = logging.getLogger(pkg["name"])
    logger.setLevel(logging.INFO)
    # create file handler which logs even debug messages

    log_file = os.path.join(pkg["install_path"], "custom_cmd.log")
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s [%(name)-12s]: %(message)s', datefmt='%H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    pkg["logger"] = logger


# def make(pkg):

pkg_names = sys.argv[1:]

pkgs_fn = "pkgs.json"

# print("Please enter sudo password:")
# subprocess.run('sudo echo "Current install directory"; pwd', shell=True)

cfg = {
    "tools_path":
    os.path.abspath(os.path.join(os.getcwd(), os.pardir)),
    "install_script_path":
    os.path.abspath(os.getcwd()),
    "tools_sh_path":
    os.path.abspath(os.path.join(os.getcwd(), os.pardir, "tools.sh")),
    "pkgs_fn":
    os.path.abspath(pkgs_fn)
}

with open(cfg["pkgs_fn"]) as json_data:
    pkgs = json.load(json_data)

if pkg_names:
    pkgs = {k: v for k, v in pkgs if k in pkg_names}

os.chdir(cfg["tools_path"])

if not os.path.exists(cfg["tools_sh_path"]):
    with open(cfg["tools_sh_path"], "w") as text_file:
        print("#!/bin/bash", file=text_file)
        print(
            "# Script for setting up the environment for all the tools",
            file=text_file)
        print(
            "# Tools installed relative to: {}".format(cfg["tools_path"]),
            file=text_file)
        print("", file=text_file)

shell_source(cfg["tools_sh_path"])

for pkg in pkgs:
    pkg.update(cfg)
    pkg["path"] = os.path.abspath(os.path.join(pkg["tools_path"], pkg["name"]))
    pkg["install_path"] = os.path.abspath(
        os.path.join(pkg["path"], "_install"))

    os.chdir(pkg["tools_path"])
    if not os.path.exists(pkg["name"]):
        os.mkdir(pkg["name"])

    if not os.path.exists(pkg["install_path"]):
        os.mkdir(pkg["install_path"])

    create_logger(pkg)

# for pkg in pkgs:
#     install_deps(pkg)


def copyanything(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc:  # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else:
            raise


for pkg in pkgs:

    pkg["logger"].info("Installation started.")
    os.chdir(pkg["install_script_path"])

    if "copy" in pkg:
        pkg["logger"].info("Copying package files...")
        for cmd in pkg["copy"]:
            for file in glob.glob(cmd[0].format(**pkg)):
                pkg["logger"].info("Copying {} to {}".format(
                    file, cmd[1].format(**pkg)))
                copyanything(
                    file,
                    os.path.join(cmd[1].format(**pkg), os.path.basename(file)))

    os.chdir(pkg["path"])
    if "url" in pkg:
        download_and_untar(pkg)

    if "git" in pkg:
        clone_git(pkg)

    custom_run(pkg, "pre_custom_run")

    flow = None
    if "flow" in pkg:
        pkg["logger"].info("Using {} flow.".format(pkg["flow"]))
        loader = importlib.machinery.SourceFileLoader(
            "", os.path.join(pkg["install_script_path"], pkg["flow"]))
        flow = loader.load_module()
        os.chdir(pkg["path"])
        flow.flow(pkg)

    os.chdir(pkg["path"])
    set_env(pkg)
    custom_run(pkg, "post_custom_run")

    pkg["logger"].info("Installation finished successfully!")
