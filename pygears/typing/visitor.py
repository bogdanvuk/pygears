class TypingVisitorBase:
    def visit(self, type_, field=None, **kwds):
        for c in type_.mro():
            visit_func_name = f'visit_{c.__name__}'

            if hasattr(self, visit_func_name):
                return getattr(self, visit_func_name)(type_, field, **kwds)

        else:
            return self.visit_default(type_, field, **kwds)

    def visit_Union(self, type_, field, **kwds):
        for t, f in zip(type_.types, type_.fields):
            self.visit(t, f)

    def visit_Int(self, type_, field, **kwds):
        pass

    def visit_Integer(self, type_, field, **kwds):
        pass

    def visit_Bool(self, type_, field, **kwds):
        pass

    def visit_Uint(self, type_, field, **kwds):
        pass

    def visit_Ufixp(self, type_, field, **kwds):
        pass

    def visit_Fixp(self, type_, field, **kwds):
        pass

    def visit_default(self, type_, field, **kwds):
        if hasattr(type_, 'fields'):
            return {
                f: self.visit(t, f, **kwds)
                for t, f in zip(type_, type_.fields)
            }
        else:
            try:
                return tuple(self.visit(t, **kwds) for t in type_)
            except TypeError:
                pass
