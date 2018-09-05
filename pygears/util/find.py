from pygears import registry


def _find_rec(path, root):
    parts = path.split("/")

    if parts[0] == '..':
        return _find_rec("/".join(parts[1:]), root.parent)

    for c in root.child:
        if hasattr(c, 'basename') and c.basename == parts[0]:
            child = c
            break
    else:
        raise ModuleNotFoundError()

    if len(parts) == 1:
        return child
    else:
        return _find_rec("/".join(parts[1:]), child)


def find(path, root=None):
    if path.startswith('/'):
        path = path[1:]
        root = registry('HierRoot')
    else:
        if path.startswith('./'):
            path = path[2:]

        root = registry('CurrentModule')

    if path == '':
        return root

    try:
        return _find_rec(path, root)
    except ModuleNotFoundError:
        raise ModuleNotFoundError(f'No module found on path "{path}"')
