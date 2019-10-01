from pygears import gear
from pygears.lib import ccat


def din_cat(f, other):
    @gear
    def din_cat_impl(cfg, din):
        return ccat(din, cfg) | f

    return din_cat_impl(other)
