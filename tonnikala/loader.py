from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala.syntaxes.tonnikala import parse as parse_tonnikala
from tonnikala.syntaxes.chameleon import parse as parse_chameleon
from os import path
from tonnikala.languages.python.generator import Generator as PythonGenerator
from tonnikala.languages.javascript.generator import Generator as JavascriptGenerator
from tonnikala.runtime import python
import six

if six.PY3:
    import builtins as __builtin__
else:
    import __builtin__

class Helpers():
    pass

helpers = Helpers()
helpers.literal = lambda x: x

def get_builtins_with_chain(chain=[ helpers ]):
    builtins = {}
    for i in [ __builtin__ ] + list(reversed(chain)):
        for j in dir(i):
            if not j.startswith('__') and not j.endswith('__'):
                builtins[j] = getattr(i, j)

    return builtins

_builtins = None
def get_builtins():
    global _builtins
    if _builtins is None:
        _builtins = get_builtins_with_chain()

    return _builtins

NOT_FOUND = object()

def make_template_context(context):
    rv = get_builtins().copy()
    rv.update(context)
    return rv


class Template(object):
    def __init__(self, binder):
        self.binder_func = binder

    def bind(self, context):
        self.binder_func(context)

    def render(self, context, funcname='__main__'):
        context = make_template_context(context)
        self.bind(context)
        return context[funcname]()


parsers = {
    'tonnikala': parse_tonnikala,
    'chameleon': parse_chameleon
}

class Loader(object):
    def __init__(self, debug=False, syntax='tonnikala'):
        self.debug = debug
        self.syntax = syntax

    def load_string(self, string, filename="<string>"):
        parser_func = parsers.get(self.syntax)
        if not parser_func:
            raise ValueError("Invalid parser syntax %s: valid syntaxes: %r"
                % sorted(parser.keys))

        tree = parser_func(filename, string)
        code = PythonGenerator(tree).generate_ast()

        if self.debug:
            import ast

            print(ast.dump(code))

            try:
                import astor
                print(astor.codegen.to_source(code))
            except ImportError:
                print("Not reversing AST to source as astor was not installed")


        runtime = python.TonnikalaRuntime()
        runtime.loader = self

        glob = {
            '__tonnikala__': runtime,
            'literal':       lambda x: x
        }

        compiled = compile(code, '<string>', 'exec')
        exec(compiled, glob, glob)
        template_func = glob['__tk__binder__']
        return Template(template_func)


import codecs
import os
from errno import ENOENT


class FileLoader(Loader):
    def __init__(self, paths=[], debug=False, syntax='tonnikala'):
        super(FileLoader, self).__init__(debug=debug, syntax=syntax)

        self.cache = {}
        self.paths = list(paths)

    def add_path(self, *a):
        self.paths.extend(a)

    def resolve(self, name):
        for i in self.paths:
            path = os.path.abspath(os.path.join(i, name))
            if os.path.exists(path):
                return path

        return None

    def load(self, name):
        template = self.cache.get(name)
        if template:
            return template

        path = self.resolve(name)
        if not path:
            raise OSError(ENOENT, "File not found: %s" % name)

        with codecs.open(path, 'r', encoding='UTF-8') as f:
           contents = f.read()

        template = self.load_string(contents, filename=path)
        self.cache[name] = template
        return template


def load_template():
    pass
