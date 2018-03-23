import os
from shutil import copyfile


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
