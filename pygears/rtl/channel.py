from pygears.core.hier_node import HierVisitorBase
from pygears.svgen.util import svgen_visitor
from pygears.rtl.intf import RTLIntf


def is_in_subbranch(root, node):
    if node is None:
        return True

    root_path = root.name.split('/')
    node_path = node.name.split('/')

    # if len(root_path) > len(node_path) + 1:
    if len(root_path) > len(node_path):
        return False

    for r, n in zip(root_path, node_path):
        if r != n:
            return False
    else:
        return True


@svgen_visitor
class RTLOutChannelVisitor(HierVisitorBase):
    def RTLNode(self, node):
        super().HierNode(node)
        if node.parent is None:
            return True

        # print(node.name)
        # if node.name == 'is_ifm_mover/do_if/fmap':
        #     import pdb
        #     pdb.set_trace()

        for p in node.out_ports:
            cons_intf = p.consumer
            consumers_at_same_level_or_sublevel = [
                cons_p in node.parent.out_ports or is_in_subbranch(cons_intf.parent, cons_p.node.parent)
                for cons_p in cons_intf.consumers
            ]
            if not all(consumers_at_same_level_or_sublevel) or (not cons_intf):
                # print(f'Node: {node.name}')
                # print(f'    {consumers_at_same_level_or_sublevel}')

                # import pdb
                # pdb.set_trace()
                # print("Here!")

                cons_intf.parent.child.remove(cons_intf)
                cons_intf.parent.parent.add_child(cons_intf)

                cons_intf.disconnect(p)
                node.parent.add_out_port(
                    p.basename, consumer=cons_intf, dtype=cons_intf.dtype)

                out_port = node.parent.out_ports[-1]
                cons_intf.producer = out_port

                local_cons = [
                    port for port, same_lvl in zip(
                        cons_intf.consumers,
                        consumers_at_same_level_or_sublevel) if same_lvl
                ]

                local_intf = RTLIntf(node.parent, cons_intf.dtype, producer=p)
                local_intf.connect(out_port)
                p.consumer = local_intf

                for port in local_cons:
                    cons_intf.consumers.remove(port)
                    local_intf.connect(port)

        return True


@svgen_visitor
class RTLChannelVisitor(HierVisitorBase):
    def RTLNode(self, node):
        for p in node.in_ports:
            prod_intf = p.producer

            parent = node.parent
            while parent is not None:
                if (prod_intf is not None and prod_intf.parent != parent
                        and (not parent.is_descendent(prod_intf.parent))):

                    parent.add_in_port(
                        p.basename, producer=prod_intf, dtype=prod_intf.dtype)
                    in_port = parent.in_ports[-1]

                    local_cons = [
                        port for port in prod_intf.consumers
                        if parent.is_descendent(port.node)
                    ]

                    local_intf = RTLIntf(
                        parent, prod_intf.dtype, producer=in_port)

                    for port in local_cons:
                        prod_intf.consumers.remove(port)
                        local_intf.connect(port)

                    prod_intf.connect(in_port)

                parent = parent.parent
