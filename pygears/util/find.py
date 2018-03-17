from pygears import registry


def _find_rec(path, root):
    parts = path.split("/")

    for c in root.child:
        if hasattr(c, 'basename') and c.basename == parts[0]:
            child = c
            break
    else:
        raise ModuleNotFoundError()

    if len(parts) == 1:
        return c
    else:
        return _find_rec("/".join(parts[1:]), child)


def find(path, root=None):
    if not root:
        root = registry('HierRoot')

    path = path[len(root.name) + 1:]
    if path == '':
        return root

    try:
        return _find_rec(path, root)
    except ModuleNotFoundError:
        raise ModuleNotFoundError(f'No module found on path "{path}"')
