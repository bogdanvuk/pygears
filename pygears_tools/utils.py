import urllib.request
import tarfile
import io
import sys
import subprocess
import os
import shutil


def get_url_archive_file_name(pkg):
    return os.path.basename(pkg["url"])


def get_url_archive_path(pkg):
    return os.path.join("_install", get_url_archive_file_name(pkg))


def download_source(pkg):
    fn = get_url_archive_file_name(pkg)

    def dlProgress(count, blockSize, totalSize):
        percent = int(count * blockSize * 100 / totalSize)
        sys.stdout.write("\rProgress: %d%%" % percent)
        sys.stdout.flush()

    pkg["logger"].info("Downloading " + pkg["url"])
    urllib.request.urlretrieve(pkg["url"], get_url_archive_path(pkg),
                               dlProgress)
    sys.stdout.write("\n")
    return fn


class ProgressFileObject(io.FileIO):
    def __init__(self, path, pkg, *args, **kwargs):
        self._total_size = os.path.getsize(path)
        self._fn = os.path.basename(path)
        self._last_percent = -1
        self._pkg = pkg
        io.FileIO.__init__(self, path, *args, **kwargs)

    def read(self, size):
        percent = int(self.tell() * 100 / self._total_size)
        if percent != self._last_percent:
            self._last_percent = percent
            # sys.stdout.write("\r[" + pkg["name"] + "] Downloading " + self._fn + "... [%d%%]" % percent)
            sys.stdout.write("\rProgress: %d%%" % percent)
            sys.stdout.flush()

        return io.FileIO.read(self, size)


def untar(pkg):
    pkg["logger"].info("Unpacking " + get_url_archive_file_name(pkg))
    tar = tarfile.open(
        fileobj=ProgressFileObject(get_url_archive_path(pkg), pkg))
    tar.extractall("_install")
    tar.close()
    sys.stdout.write("\n")


def download_and_untar(pkg):
    fn = get_url_archive_path(pkg)
    if not os.path.exists(fn):
        download_source(pkg)
    else:
        pkg["logger"].info(
            "Source archive already available and will be reused.")

    src_dir = pkg["src_root_path"].format(**pkg)
    unpack = False
    if not os.path.exists(src_dir):
        unpack = True
    else:
        srctime = os.path.getmtime(fn)
        tartime = os.path.getmtime(src_dir)

        if tartime < srctime:
            unpack = True
            shutil.rmtree(src_dir)
            pkg["logger"].info("Source older than archive, updating...")

    if unpack:
        untar(pkg)
    else:
        pkg["logger"].info("Sources already present and up to date.")


def install_deps(pkg):
    if not "deps" in pkg:
        return True

    pkg["logger"].info(
        "Installing dependencies. Output redirected to dependencies.log .")
    subprocess.run(
        "sudo apt install -y " + pkg["deps"] + " > " +
        os.path.join(pkg["path"], "_install", "dependencies.log") + " 2>&1",
        shell=True,
        check=True)


def configure(pkg):

    os.chdir(pkg["src_root_path"].format(**pkg))

    if "configure" in pkg:
        pkg["logger"].info(
            "Running auto configure. Output redirected to configure.log .")
        subprocess.check_output(
            "./configure --prefix=" + pkg["path"] + " " + pkg["configure"] +
            " > ../configure.log 2>&1",
            shell=True)
    os.chdir(pkg["path"])


def cmake(pkg):
    os.chdir(pkg["src_root_path"].format(**pkg))
    if not "cmake_cfg" in pkg:
        pkg["cmake_cfg"] = ""

    if os.path.exists("build"):
        shutil.rmtree("build")

    os.mkdir("build")
    os.chdir("build")
    pkg["logger"].info("Running CMake. Output redirected to cmake.log .")
    subprocess.check_output(
        "cmake -DCMAKE_INSTALL_PREFIX:PATH={} {} .. > ../../cmake.log 2>&1".
        format(pkg["path"], pkg["cmake_cfg"]),
        shell=True)
    pkg["src_root_path"] = os.getcwd()
    os.chdir(pkg["path"])


def make(pkg):
    os.chdir(pkg["src_root_path"].format(**pkg))

    pkg["logger"].info("Running make. Output redirected to make.log .")
    subprocess.check_output("make -j8 > ../make.log 2>&1", shell=True)
    pkg["logger"].info(
        "Running make install. Output redirected to make_install.log .")
    subprocess.check_output(
        "make install > ../make_install.log 2>&1", shell=True)
    os.chdir(pkg["path"])


def clone_git(pkg):
    clone_dir = pkg["src_root_path"].format(**pkg)
    if not os.path.exists(clone_dir):
        pkg["logger"].info(
            "Cloning git repo. Output redirected to git_clone.log .")
        subprocess.check_output(
            "git clone " + pkg["git"] + " " + clone_dir +
            " > git_clone.log 2>&1",
            shell=True)
    else:
        pkg["logger"].info(
            "Source git repo already available and will be reused.")


def shell_source(script):
    """Sometime you want to emulate the action of "source" in bash,
    settings some environment variables. Here is a way to do it."""
    pipe = subprocess.Popen(
        ". %s; env" % script, stdout=subprocess.PIPE, shell=True)
    output = pipe.communicate()[0].decode()
    env = {}
    for line in output.splitlines():
        try:
            keyval = line.split("=", 1)
            env[keyval[0]] = keyval[1]
        except:
            pass

    os.environ.update(env)


def set_env(pkg):
    if not "env" in pkg:
        return True

    pkg["logger"].info("Exporting the environment variables.")
    with open(pkg["tools_sh_path"], "a") as text_file:
        print("", file=text_file)
        print("# Environment for {}".format(pkg["name"]), file=text_file)
        for cmd in pkg["env"]:
            print(cmd.format(**pkg), file=text_file)

    shell_source(pkg["tools_sh_path"])


def custom_run(pkg, cmd_set):
    if not cmd_set in pkg:
        return True

    pkg["logger"].info(
        "Running custom package commands. Output redirected to custom_cmd.log ."
    )

    log_file = os.path.join(pkg["install_path"], "custom_cmd.log")
    for cmd in pkg[cmd_set]:
        cmd = cmd.format(**pkg)
        pkg["logger"].info('Running command: "{}"'.format(cmd))
        subprocess.check_output(
            "{} > {} 2>&1".format(cmd, log_file), shell=True)
