import os
from pygears import reg


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
        root = reg['gear/root']
    else:
        if path.startswith('./'):
            path = path[2:]

        root = reg['gear/current_module']

    if path == '':
        return root

    module_path, port_name = os.path.splitext(path)

    try:
        module = _find_rec(module_path, root)
    except ModuleNotFoundError:
        return None

    if not port_name:
        return module
    else:
        port_name = port_name[1:]
        for p in module.in_ports + module.out_ports + module.local_intfs:
            if p.basename == port_name:
                return p

        return None
