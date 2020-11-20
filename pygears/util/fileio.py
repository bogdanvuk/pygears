import os
from shutil import copyfile


def expand(fn):
    return os.path.abspath(os.path.expandvars(os.path.expanduser(fn)))


def copy_file(fn, outdir, src):

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    dest = os.path.join(outdir, fn)
    copyfile(src, dest)

    return dest


def save_file(fn, outdir, content):

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    dest = os.path.join(outdir, fn)
    with open(os.path.join(outdir, fn), 'w') as content_file:
        content_file.write(content)

    return dest


def save_if_changed(fn, outdir, content):
    content_old = ''
    file_path = os.path.join(outdir, fn)
    if os.path.exists(file_path):
        with open(file_path) as f:
            content_old = f.read()

    if content_old != content:
        save_file(os.path.basename(fn), outdir, content)


def find_in_dirs(fn, dirs):
    for d in dirs:
        full_path = os.path.join(d, fn)
        if os.path.exists(full_path):
            return full_path
    else:
        return None


def get_main_script():
    import __main__

    if not hasattr(__main__, '__file__'):
        return None

    return os.path.basename(__main__.__file__)
