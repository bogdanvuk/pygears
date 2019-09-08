from pygears.core.hier_node import HierVisitorBase
from pygears.rtl import flow_visitor
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


@flow_visitor
class RTLOutChannelVisitor(HierVisitorBase):
    def RTLNode(self, node):
        super().HierNode(node)
        if node.parent is None:
            return True

        for p in node.out_ports:
            cons_intf = p.consumer
            consumers_at_same_level_or_sublevel = [
                # cons_p in node.parent.out_ports or is_in_subbranch(cons_intf.parent, cons_p.node.parent)
                cons_p in node.parent.out_ports
                or cons_intf.parent.has_descendent(cons_p.node)
                for cons_p in cons_intf.consumers
            ]

            if not all(consumers_at_same_level_or_sublevel) or (not cons_intf):
                cons_intf.parent.child.remove(cons_intf)
                cons_intf.parent.parent.add_child(cons_intf)

                cons_intf.disconnect(p)
                node.parent.add_out_port(p.basename,
                                         consumer=cons_intf,
                                         dtype=cons_intf.dtype)

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


from pygears.core.gear import OutSig, InSig


def is_driven_by_node(node, name):
    for s in node.params['signals']:
        if isinstance(s, OutSig):
            if s.name in node.params['sigmap']:
                if name == node.params['sigmap'][s.name]:
                    return s
            else:
                if name == s.name:
                    return s
    else:
        return None


def find_signal_driver_port(parent, name):
    for node in parent.local_modules():
        if is_driven_by_node(node, name):
            return True

    for s in parent.params['signals']:
        if isinstance(s, InSig):
            if s.name == name:
                return True

    return False


@flow_visitor
class RTLSigChannelVisitor(HierVisitorBase):
    def RTLNode(self, node):
        self.HierNode(node)

        if node.parent:
            for s in node.params['signals']:
                if s.name not in node.params['sigmap']:
                    node.params['sigmap'] = node.params['sigmap'].copy()
                    node.params['sigmap'][s.name] = s.name

            for s in node.params['signals']:
                if isinstance(s, InSig):
                    sig_name = node.params['sigmap'][s.name]

                    if not find_signal_driver_port(node.parent, sig_name):
                        if not isinstance(node.parent.params['signals'], list):
                            node.parent.params['signals'] = list(
                                node.parent.params['signals'])

                        node.parent.params['signals'] = node.parent.params[
                            'signals'].copy()
                        node.parent.params['signals'].append(s)

        return True


@flow_visitor
class RTLChannelVisitor(HierVisitorBase):
    def RTLNode(self, node):
        for p in node.in_ports:
            prod_intf = p.producer

            parent = node.parent
            while parent is not None:
                if (prod_intf is not None and prod_intf.parent != parent
                        and (not parent.has_descendent(prod_intf.parent))):

                    parent.add_in_port(p.basename,
                                       producer=prod_intf,
                                       dtype=prod_intf.dtype)
                    in_port = parent.in_ports[-1]

                    local_cons = [
                        port for port in prod_intf.consumers
                        if parent.has_descendent(port.node)
                    ]

                    local_intf = RTLIntf(parent,
                                         prod_intf.dtype,
                                         producer=in_port)

                    for port in local_cons:
                        prod_intf.consumers.remove(port)
                        local_intf.connect(port)

                    prod_intf.connect(in_port)

                parent = parent.parent
