from .utils import configure, make


def flow(pkg):
    configure(pkg)
    make(pkg)

    return True
