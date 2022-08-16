from dataclasses import dataclass

from .control import Control
from .parser import Ast, EnumDeclaration, Expression, ExternFunction, Import, Name, Type, StructDeclaration, Function, Body, Let
from .lexer import lex, Literal
from .parser import parse

@dataclass
class Scope:
    name: Name
    constants: dict[Name, tuple[Name, Expression]]
    variables: dict[Name, tuple[Name, Expression]]
    functions: dict[Name, dict[tuple[Name], Function]]
    modules: dict[Name, "Scope"]
    structs: dict[Type, StructDeclaration]
    enums: dict[Type, EnumDeclaration]
    indent: int=0
    
    def copy(self):
        return type(self)(self.name, dict(self.constants), dict(self.variables), dict(self.functions), dict(self.modules), dict(self.structs), dict(self.enums), self.indent + 1)
    
    @property
    def types(self):
        types_ = dict(self.structs)
        
        for module in self.modules.values():
            if type(module) is Scope:
                types_ |= module.types
        
        return types_

def check_body(scope: Scope, body: Body):
    for line in body.lines:
        if type(line) is Let:
            scope.variables[line.name] = (line.kind, line.value)

    return body

def check_function(scope: Scope, function: Function):
    for name, kind in function.parameters.items():
        scope.variables[name] = (kind, None)

        if name in ("str", "int", "pointer"):
            raise ValueError(f'parameter names must not conflict with types. {name} == {name}. at {function.name}')
    
    function.body = check_body(scope, function.body)
    return function, scope

def check_module(path: Expression, checked_modules=set()):
    tokens = list(lex(Control(open(path.value.replace('.', '/') + '.greek').read())))
    asts = list(parse(Control(tokens)))
    
    return check(asts, path, checked_modules)

def check_struct_declaration(scope: Scope, struct_declaration: StructDeclaration):
    scope = scope.copy()

    for signatures in struct_declaration.functions.values():
        for function in signatures.values():
            scope.functions.setdefault(function.name, {})

            function, function_scope = check_function(scope, function)
            scope.functions[function.name][tuple(function.parameters.values())] = function, function_scope
            function.owner = struct_declaration
    
    scope.modules[f'{scope.name.value}.{struct_declaration.kind.name.value}'] = struct_declaration

    return (struct_declaration, scope)

def check_enum_declaration(scope: Scope, enum_declaration: EnumDeclaration):
    for i, name in enumerate(enum_declaration.names):
        scope.variables[name] = (Type(Name('int')), Literal(i))

    return enum_declaration, scope

def check(asts: Ast, name: Name, checked_modules=set()):
    scope = Scope(name, dict(), dict(), dict(), dict(), dict(), dict())

    for ast in asts:
        if type(ast) is Import:
            if ast.as_path in checked_modules:
                raise RecursionError(f"recursive import of module {ast.as_path} at {name}")
            
            module = check_module(ast.as_path, checked_modules | {ast.as_path})
            scope.modules[ast.as_path] = module

            for signatures in module.functions.values():
                for function in signatures.values():
                    if type(function) is ExternFunction:
                        scope.modules[function.name] = function

        elif type(ast) is Function:
            scope.functions.setdefault(ast.name, {})
            scope.functions[ast.name][tuple(ast.parameters.values())] = check_function(scope.copy(), ast)
        elif type(ast) is ExternFunction:
            scope.functions.setdefault(ast.name, {})
            scope.functions[ast.name][tuple(ast.parameters.values())] = (ast, scope)
        elif type(ast) is StructDeclaration:
            if ast.kind in scope.structs:
                raise NameError(f"type struct '{ast.kind.name}' already declared in module '{scope.name.value}'")

            struct, struct_scope = check_struct_declaration(scope, ast)
            scope.structs[ast.kind] = (struct, struct_scope)

            struct_scope.structs |= scope.structs
        elif type(ast) is EnumDeclaration:
            if ast.kind in scope.enums:
                raise NameError(f"type enum '{ast.kind.name}' already declared in module '{scope.name.value}'")
            
            scope.enums[ast.kind] = check_enum_declaration(scope, ast)

        elif type(ast) is Let:
            scope.constants[ast.name] = (ast.kind, ast.value)

    return scope