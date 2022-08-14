from dataclasses import dataclass

from .control import Control
from .parser import Ast, Expression, ExternFunction, Import, Name, Type, StructDeclaration, Function, Body, Let
from .lexer import lex
from .parser import parse

@dataclass
class Scope:
    name: Name
    variables: dict[Name, tuple[Name, Expression]]
    functions: dict[Name, dict[tuple[Name], Function]]
    modules: dict[Name, "Scope"]
    structs: dict[Type, StructDeclaration]
    indent: int=0
    

    def copy(self):
        return type(self)(self.name, dict(self.variables), dict(self.functions), dict(self.modules), dict(self.structs), self.indent + 1)

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
    
    return lint(asts, path)

def lint_struct_declaration(scope: Scope, struct_declaration: StructDeclaration):
    struct_scope = scope.copy()

    for signatures in struct_declaration.functions.values():
        for function in signatures.values():
            struct_scope.functions.setdefault(function.name, {})
            struct_scope.functions[function.name][tuple(function.parameters.values())] = lint_function(struct_scope, function)
    
    scope.modules[f'{scope.name.value}.{struct_declaration.kind.name.value}'] = struct_declaration

    return struct_declaration

def lint(asts: Ast, name: Name):
    scope = Scope(name, dict(), dict(), dict(), dict())

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
            if ast.kind in scope.structs:
                raise NameError(f"type struct '{ast.kind.name}' already declared in module '{scope.name.value}'")

            scope.structs[ast.kind] = lint_struct_declaration(scope, ast)

    return scope