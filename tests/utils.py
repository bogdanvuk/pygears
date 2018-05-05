import re
import os
import inspect
import shutil

from pygears.definitions import ROOT_DIR

re_trailing_space_rem = re.compile(r"\s+$", re.MULTILINE)
re_multispace_rem = re.compile(r"^\s+", re.MULTILINE)
re_multi_comment_rem = re.compile(r"/\*.*?\*/", re.DOTALL)
re_comment_rem = re.compile(r"//.*$", re.MULTILINE)

rem_pipe = [
    re_multi_comment_rem, re_comment_rem, re_multispace_rem,
    re_trailing_space_rem
]


def remove_unecessary(s):

    for r in rem_pipe:
        s = r.sub('', s)

    return s.strip()


def equal_on_nonspace(str1, str2):
    # print(remove_unecessary(str1))
    # print('-----------------------')
    # print(remove_unecessary(str2))
    # print('-----------------------')
    return remove_unecessary(str1) == remove_unecessary(str2)


def file_equal_on_nonspace(str1, str2):
    pass


def prepare_result_dir():
    for _, filename, _, function_name, _, _ in inspect.stack():
        if function_name.startswith('test_'):
            break
    else:
        raise Exception("Has to be run from within a test function")

    res_dir = os.path.join(
        os.path.dirname(__file__), 'result',
        os.path.splitext(filename)[0], function_name)

    try:
        shutil.rmtree(res_dir)
    except FileNotFoundError:
        pass

    os.makedirs(res_dir, exist_ok=True)

    return res_dir
