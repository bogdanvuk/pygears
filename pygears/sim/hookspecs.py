import pluggy

hookspec = pluggy.HookspecMarker('sim')


@hookspec
def sim_before_setup(sim):
    '''Before simulation setup'''


@hookspec
def sim_before_run(sim):
    '''Before simulation run'''


@hookspec
def sim_after_run(sim):
    '''After simulation run'''
