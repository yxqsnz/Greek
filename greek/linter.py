from dataclasses import dataclass

from .control import Control
from .parser import Ast, Expression, ExternFunction, Import, Name, Type, StructDeclaration, Function, Body, Let
from .lexer import lex
from .parser import parse

@dataclass
class Scope:
    variables: dict[Name, tuple[Name, Expression]]
    functions: dict[Name, dict[tuple[Name], Function]]
    modules: dict[Name, "Scope"]
    structs: dict[Type, StructDeclaration]
    indent: int=0
    name: Name=None

    def copy(self):
        return type(self)(self.variables, self.functions, self.modules, self.structs, self.indent + 1, self.name)

def lint_body(scope: Scope, body: Body):
    for line in body.lines:
        if type(line) is Let:
            scope.variables[line.name] = (line.kind, line.value)

    return body

def lint_function(scope: Scope, function: Function):
    for name, kind in function.parameters.items():
        scope.variables[name] = (kind, None)
    
    function.body = lint_body(scope, function.body)
    return function

def lint_module(path: Expression):
    tokens = list(lex(Control(open(path.value.replace('.', '/') + '.greek').read())))
    asts = list(parse(Control(tokens)))
    
    return lint(asts, name=path)

def lint(asts: Ast, name: Name=None):
    scope = Scope(dict(), dict(), dict(), dict(), name=name)

    for ast in asts:
        if type(ast) is Import:
            scope.modules[ast.as_path] = lint_module(ast.as_path)
        elif type(ast) is Function:
            scope.functions.setdefault(ast.name, {})
            scope.functions[ast.name][tuple(ast.parameters.values())] = lint_function(scope, ast)
        elif type(ast) is ExternFunction:
            scope.functions.setdefault(ast.name, {})
            scope.functions[ast.name][tuple(ast.parameters.values())] = ast
        elif type(ast) is StructDeclaration:
            scope.structs[ast.kind] = ast
            
    return scope