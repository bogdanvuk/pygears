import sys
import importlib
import pdb
import fnmatch
import inspect

fn_skip = ['<*', f'{sys.prefix}/lib/*']

module_skip = [
    'pygears.conf.*', 'pygears.core.*', 'pygears.registry', 'pygears.util.*',
    'pygears.typing.*', 'pygears.sim.*', '<*', 'pygears.lib.const'
]


def is_skipped_frame(self, frame):
    fn = frame.f_code.co_filename
    mn = frame.f_globals.get('__name__')

    # print(f'Entering: {fn}: {mn}')

    if fn is not None:
        for pattern in fn_skip:
            if fnmatch.fnmatch(fn, pattern):
                return True

    if mn is not None:
        for pattern in module_skip:
            if fnmatch.fnmatch(mn, pattern):
                return True

    return False


def do_up(self, arg):
    frame_found = 0
    new_index = self.curindex
    count = int(arg or 1)

    while not frame_found == count:
        if new_index == 0:
            self.error('Oldest frame')
            break

        new_index -= 1

        if not is_skipped_frame(self, self.stack[new_index][0]):
            frame_found += 1

    if frame_found:
        self._select_frame(new_index)


def do_down(self, arg):
    frame_found = 0
    new_index = self.curindex
    count = int(arg or 1)

    while not frame_found == count:
        new_index += 1

        if new_index == len(self.stack):
            self.error('Oldest frame')
            break

        if not is_skipped_frame(self, self.stack[new_index][0]):
            frame_found += 1

    if frame_found:
        self._select_frame(new_index)


def stop_here(self, frame):
    if is_skipped_frame(self, frame):
        return False

    if frame is self.stopframe:
        if self.stoplineno == -1:
            return False
        return frame.f_lineno >= self.stoplineno

    if not self.stopframe:
        return True
    return False


def print_stack_trace(self):
    try:
        for frame_lineno in self.stack:
            if not is_skipped_frame(self, frame_lineno[0]):
                self.print_stack_entry(frame_lineno)
    except KeyboardInterrupt:
        pass


def patch_pdb():
    tr = sys.gettrace();
    if tr:
        if not hasattr(tr, '__self__'):
            return

        p = tr.__self__
        if p is not None:
            p.stop_here = stop_here.__get__(p, pdb.Pdb)
            p.do_up = do_up.__get__(p, pdb.Pdb)
            p.do_down = do_down.__get__(p, pdb.Pdb)
            p.do_u = do_up.__get__(p, pdb.Pdb)
            p.do_d = do_down.__get__(p, pdb.Pdb)
            p.print_stack_trace = print_stack_trace.__get__(p, pdb.Pdb)

    pdb.Pdb.stop_here = stop_here
    pdb.Pdb.do_up = do_up
    pdb.Pdb.do_down = do_down
    pdb.Pdb.do_u = do_up
    pdb.Pdb.do_d = do_down
    pdb.Pdb.print_stack_trace = print_stack_trace


def unpatch_pdb():
    importlib.reload(pdb)
    tr = sys.gettrace();

    if tr:
        if not hasattr(tr, '__self__'):
            return

        p = tr.__self__

        if p is None:
            return

        if inspect.getfile(p.stop_here) == __file__:
            p.stop_here = pdb.Pdb.stop_here.__get__(p, pdb.Pdb)
            p.do_up = pdb.Pdb.do_up.__get__(p, pdb.Pdb)
            p.do_down = pdb.Pdb.do_down.__get__(p, pdb.Pdb)
            p.do_u = pdb.Pdb.do_up.__get__(p, pdb.Pdb)
            p.do_d = pdb.Pdb.do_down.__get__(p, pdb.Pdb)
            p.print_stack_trace = pdb.Pdb.print_stack_trace.__get__(p, pdb.Pdb)
