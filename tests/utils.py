import re

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
