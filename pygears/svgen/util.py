def svgen_visitor(cls):
    def svgen_action(top, conf):
        v = cls()
        v.conf = conf
        v.visit(top)
        return top

    return svgen_action
