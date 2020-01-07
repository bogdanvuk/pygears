from ..pydl import nodes as pydl


def add_to_list(orig_list, extention):
    if extention:
        orig_list.extend(
            extention if isinstance(extention, list) else [extention])


class InstanceVisitor:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        breakpoint()
        raise Exception(
            f'Method "{node.__class__.__name__}" not implemented in "{self.__class__.__name__}" visitor'
        )


class CBlockVisitor(InstanceVisitor):
    def __init__(self, hdl_visitor):
        self.hdl = hdl_visitor

    def enter_block(self, block):
        return self.ping_hdl(block.pydl_block)

    def exit_block(self):
        pass

    def visit_prolog(self, node):
        prolog_stmts = []
        if node.prolog:
            for block in node.prolog:
                curr_block = self.ping_hdl(block)
                self._add_sub(block, curr_block)
                add_to_list(prolog_stmts, curr_block)
        return prolog_stmts

    def visit_epilog(self, node):
        epilog = []
        if node.epilog:
            for block in node.epilog:
                curr_block = self.ping_hdl(block)
                self._add_sub(block, curr_block)
                add_to_list(epilog, curr_block)
        return epilog

    def visit_block(self, node):
        top = []

        add_to_list(top, self.visit_prolog(node))

        curr_block = self.enter_block(node)

        for child in node.child:
            add_to_list(curr_block.stmts, self.visit(child))

        # if stmts:
        #     self.hdl.update_defaults(curr_block)

        self.exit_block()

        add_to_list(top, curr_block)

        add_to_list(top, self.visit_epilog(node))

        # TODO: What is this about?
        # if len(top) == 1 and isinstance(top[0], pydl.CombBlock):
        #     return top[0]

        return top

    def visit_SeqCBlock(self, node):
        return self.visit_block(node)

    def visit_MutexCBlock(self, node):
        return self.visit_block(node)

    def _add_sub(self, block, curr_block):
        if isinstance(block, pydl.Block):
            for stmt in block.stmts:
                sub = self.ping_hdl(stmt)
                self._add_sub(stmt, sub)
                add_to_list(curr_block.stmts, sub)
            self.hdl.update_defaults(curr_block)

    def visit_Leaf(self, node):
        hdl_block = []
        for block in node.pydl_blocks:
            curr_block = self.ping_hdl(block)
            self._add_sub(block, curr_block)
            add_to_list(hdl_block, curr_block)
        return hdl_block

    def ping_hdl(self, block):
        return self.hdl.visit(block)


class CBlockPrinter(InstanceVisitor):
    def __init__(self):
        self.indent = 0
        self.msg = ''

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        self.msg += f'{" "*self.indent}{line}\n'

    def get_pydl(self, node):
        if hasattr(node, 'pydl_blocks'):
            pydl_nodes = []
            for block in node.pydl_blocks:
                pydl_nodes.append(block.__class__.__name__)
            return pydl_nodes

        return node.pydl_block.__class__.__name__

    def generic_visit(self, node):
        if hasattr(node, 'child'):
            self.write_line(
                f'{node.__class__.__name__}: states: {node.state_ids}, ({self.get_pydl(node)})'
            )
            self.enter_block()
            for child in node.child:
                self.visit(child)
            self.exit_block()
        else:
            self.write_line(
                f'Leaf: state {node.state_id}, {self.get_pydl(node)}')

        return self.msg


def pformat(node):
    return CBlockPrinter().visit(node)
