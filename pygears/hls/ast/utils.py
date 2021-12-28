import inspect
import types
import textwrap
import ast
import os


def get_function_source(func):
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        try:
            source = func.__source__
        except AttributeError:
            return ''

    return textwrap.dedent(source)


def get_short_lambda_ast(lambda_func):
    """Return the source of a (short) lambda function.
    If it's impossible to obtain, returns None.

    taken from: http://xion.io/post/code/python-get-lambda-code.html
    """
    try:
        source_lines, _ = inspect.getsourcelines(lambda_func)
    except (IOError, TypeError):
        return None

    # skip `def`-ed functions and long lambdas
    if len(source_lines) != 1:
        return None

    source_text = os.linesep.join(source_lines).strip()

    # find the AST node of a lambda definition
    # so we can locate it in the source code
    source_ast = ast.parse(source_text)
    lambda_node = next((node for node in ast.walk(source_ast) if isinstance(node, ast.Lambda)),
                       None)
    if lambda_node is None:  # could be a single line `def fn(x): ...`
        return None

    return lambda_node


def is_lambda_function(obj):
    return isinstance(obj, types.LambdaType) and obj.__name__ == (lambda: None).__name__


def get_function_ast(func):
    if is_lambda_function(func):
        lambda_ast = get_short_lambda_ast(func)
        lambda_ast.body = [ast.Return(lambda_ast.body)]
        return ast.fix_missing_locations(lambda_ast)
    else:
        src = get_function_source(func)
        if not src:
            raise SyntaxError(f"Function '{func.__qualname__}()' not supported")

        return ast.parse(src).body[0]

def is_func_empty(func):
    # TODO: We are doing AST generation at least twice, performance impact?
    body = get_function_ast(func).body
    if isinstance(body[0], ast.Pass):
        return True

    if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Ellipsis):
        return True

    return False


def get_property_type(prop):
    assert isinstance(prop, property)

    return prop.fget.__annotations__['return']


def add_to_list(orig_list, extension):
    if extension:
        if not isinstance(extension, list):
            orig_list.append(extension)
        else:
            orig_list.extend(extension)
