import os
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
        root = registry('gear/hier_root')
    else:
        if path.startswith('./'):
            path = path[2:]

        root = registry('gear/current_module')

    if path == '':
        return root

    module_path, intf_name = os.path.splitext(path)

    try:
        module = _find_rec(module_path, root)
    except ModuleNotFoundError:
        raise ModuleNotFoundError(f'No module found on path "{module_path}"')

    if not intf_name:
        return module
    else:
        intf_name = intf_name[1:]
        for i, p in enumerate(module.in_ports):
            if p.basename == intf_name:
                return module.in_ports[i]

        for i, p in enumerate(module.out_ports):
            if p.basename == intf_name:
                return module.out_ports[i]

        raise ModuleNotFoundError(f'No module found on path "{path}"')
