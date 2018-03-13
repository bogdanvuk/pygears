class TypingVisitorBase:
    def visit(self, type_, field=None):
        visit_func_name = f'visit_{type_.__name__.lower()}'

        visit_func = getattr(self, visit_func_name, self.visit_default)

        return visit_func(type_, field)

    def visit_union(self, type_, field):
        for t, f in zip(type_.types(), type_.fields):
            self.visit(t, f)

    def visit_int(self, type_, field):
        pass

    def visit_bool(self, type_, field):
        pass

    def visit_uint(self, type_, field):
        pass

    def visit_default(self, type_, field):
        if hasattr(type_, 'fields'):
            for t, f in zip(type_, type_.fields):
                self.visit(t, f)
        else:
            try:
                for t in type_:
                    self.visit(t)
            except TypeError:
                pass
