from pygears.core.hier_node import HierVisitorBase
from pygears.svgen.util import svgen_visitor
from pygears.rtl.intf import RTLIntf


@svgen_visitor
class RTLChannelVisitor(HierVisitorBase):
    def RTLNode(self, node):
        if node.parent is None:
            return

        for p in node.in_ports:
            prod_intf = p.producer
            parent = node.parent

            if (prod_intf is not None and prod_intf.parent != parent
                    and (not parent.is_descendent(prod_intf.parent))):

                parent.add_in_port(
                    p.basename, producer=prod_intf, dtype=prod_intf.dtype)
                in_port = parent.in_ports[-1]

                local_cons = [
                    port for port in prod_intf.consumers
                    if parent.is_descendent(port.node)
                ]

                local_intf = RTLIntf(parent, prod_intf.dtype, producer=in_port)

                for port in local_cons:
                    prod_intf.consumers.remove(port)
                    local_intf.connect(port)

                prod_intf.connect(in_port)

        # for p in self.out_ports():
        #     consumers_at_same_level_or_sublevel = [
        #         is_in_subbranch(p['intf'].parent, c[0])
        #         for c in p['intf'].consumers
        #     ]
        #     if not all(consumers_at_same_level_or_sublevel) or (
        #             not p['intf'].consumers):
        #         self.parent.out_port_make(p, self)
