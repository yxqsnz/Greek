from dataclasses import dataclass

from .source import Source
from .lexer import Lexer, Literal, Type
from .parser import EnumDeclaration, Parenthesized, Parser, Assignment, BinaryOperation, Body, Call, Dot, Else, Expression, Extern, FunctionHead, If, Import, Item, Let, Name, Return, StructDeclaration, FunctionDeclaration, While
from .parser import Ast

@dataclass
class Module:
    name: str
    modules: dict[str, "Module"]
    variables: dict[str, Let]
    constants: dict[str, Let]
    structs: dict[str, StructDeclaration]
    enums: dict[str, StructDeclaration]
    functions: dict[str, dict[tuple[str], FunctionDeclaration]]

    def copy(self):
        return type(self)(self.name, dict(self.modules), dict(self.variables), dict(self.constants), dict(self.structs), dict(self.enums), dict(self.functions))
    
    @property
    def all_functions(self):
        functions = dict(self.functions)

        for module in self.modules.values():
            for function_name, function_signature in module.functions.items():
                functions[Name(f'{module.name}.{function_name.format}', function_name.line)] = function_signature
        
        return functions
    
    @property
    def all_structs(self):
        structs = dict(self.structs)

        for module in self.modules.values():
            for struct in module.structs.values():
                structs[struct.name] = struct

        return structs

    @classmethod
    def new(cls, name: str):
        return cls(name, dict(), dict(), dict(), dict(), dict(), dict())

@dataclass
class Hint:
    ast: Ast
    kind: Expression

class Checker:
    def __init__(self, asts: tuple[Ast], module: Module):
        self.asts = asts
        self.module = module
    
    def check_struct_declaration(self, struct_declaration: StructDeclaration):
        if type(struct_declaration.name) is Item:
            for generic_variable in struct_declaration.name.right.values:
                if generic_variable not in struct_declaration.members.values():
                    raise ValueError(f"generic variable {generic_variable.value} left unused in struct {struct_declaration.name.left.value}. at line {struct_declaration.line} in module '{self.module.name}'")
        
        self.module.structs[struct_declaration.name] = struct_declaration

        old_self_module = self.module
        self.module = self.module.copy()
        self.module.name = struct_declaration.name.format

        for signatures in struct_declaration.methods.values():
            for method in signatures.values():
                if type(method) is FunctionDeclaration:
                    method.head.struct = struct_declaration

                self.check_function_declaration(method)
        
        self.module = old_self_module

        return struct_declaration
    
    def check_let(self, let: Let, declare=True):
        if type(let.kind) is Item:
            if let.kind.right.values[0].value != let.value.kind.right.values[0].value:
                raise TypeError(f"let type mismatch, expected '{let.kind.format}' found '{let.value.kind.format}'. at line {let.line} in module '{self.module.name}'")
        else:
            let_value_kind = self.check_expression(let.value)

            if let.kind != let_value_kind:
                raise TypeError(f"let type mismatch, expected '{let.kind.format}' found '{let_value_kind.format}'. at line {let.line} in module '{self.module.name}'")
        
        if declare:
            if let.name.value in self.module.variables:
                raise NameError(f"variable {let.name.value} is already declared. at line {let.line} in module '{self.module.name}'")

            self.module.variables[let.name.value] = let 

        return let_value_kind
    
    def check_assignment(self, assignment: Assignment):
        if type(assignment.head) is Dot:
            if assignment.head.left not in self.module.variables:
                raise NameError(f"variable {assignment.head.format} not found in the current scope. at line {assignment.line} in module '{self.module.name}'")
        
        elif assignment.head.value not in self.module.variables:
            raise NameError(f"variable {assignment.head.format} not found in the current scope. at line {assignment.line} in module '{self.module.name}'")
        
        if type(assignment.head) is Dot:
            let = self.module.variables[assignment.head.left]
        else:
            let = self.module.variables[assignment.head.value]
        
        if type(let) is not Let:
            let_kind = let
        else:
            let_kind = self.check_let(let, declare=False)

        assignment_value_kind = self.check_expression(assignment.value)

        if type(assignment.head) is Item:
            indice = assignment.head.right.values[0]
            indice_kind = self.check_expression(indice)

            if indice_kind != Name('int'):
                raise TypeError(f"item indice must be an integer, found '{indice.format}' of type '{indice_kind.format}'. at line {assignment.line} in module '{self.module.name}'")

            if type(let_kind) is Item and let_kind.left == Name('array'):
                if let_kind.right.values[0] != assignment.value.kind:
                    raise TypeError(f"variable {assignment.head.format} expects '{let_kind.right.values[0].format}' but a '{assignment.value.kind.format}' was provided. line {assignment.line} in module '{self.module.name}'")
            elif let_kind != Name('str'):
                raise TypeError(f"variable '{let.name.value}' of type '{let_kind.format}' can't be indexed. at line {assignment.line} in module '{self.module.name}'")
            
            assignment_value_kind = self.check_expression(assignment.value)

            if Name('char') != assignment_value_kind and Name('int') != assignment_value_kind:
                raise TypeError(f"variable {assignment.head.format} expects 'byte' or 'int', but a '{assignment_value_kind.format}' was provided. line {assignment.line} in module '{self.module.name}'")
        
        elif type(assignment.value) is Item:
            if let_kind != assignment_value_kind:
                raise TypeError(f"variable {assignment.head.format} expects '{let_kind.format}' but a '{assignment_value_kind.format}' was provided. line {assignment.line} in module '{self.module.name}'")

        elif let_kind != assignment_value_kind:
            raise TypeError(f"variable {assignment.head.format} expects '{let_kind.format}' but a '{assignment_value_kind.format}' was provided. line {assignment.line} in module '{self.module.name}'")

        return assignment
    
    def check_expression(self, expression: Expression):
        if type(expression) is Name:
            if expression not in self.module.variables:
                raise NameError(f"{expression.format} is undeclared. at line {expression.line} in module '{self.module.name}'")
            
            let = self.module.variables[expression]

            if type(let) is Name or type(let) is Type:
                return let

            return let.kind
        elif type(expression) is Call:
            functions = self.module.all_functions

            if expression.head.format not in functions:
                if type(expression.head) is Dot:
                    if expression.head.left not in self.module.all_structs and expression.head.left not in self.module.variables:
                        raise NameError(f"function '{expression.head.left.format}' not found in this scope. at line {expression.line} in module '{self.module.name}'")
                
                else:
                    raise NameError(f"function '{expression.head.format}' not found in this scope. at line {expression.line} in module '{self.module.name}'")
            
            call_signature = tuple(self.check_expression(argument) for argument in expression.arguments)

            if type(expression.head) is Dot:
                if expression.head.left in self.module.all_structs:
                    fun_signatures = self.module.all_structs[expression.head.left].methods[expression.head.right.format]
                elif expression.head.left in self.module.variables:
                    variable = self.module.variables[expression.head.left]

                    if type(variable) is Let:
                        variable = variable.kind

                    call_signature = (variable, *call_signature)
                    fun_signatures = self.module.all_structs[variable].methods[expression.head.right.format]
                else:
                    fun_signatures = functions[expression.head.format]
            else:
                fun_signatures = functions[expression.head.format]
            
            signature_found = None

            for signature in fun_signatures.keys():
                if signature == call_signature:
                    signature_found = signature

            if signature_found is None:
                raise NameError(f"can't find a function with signature '{expression.head.format}({', '.join(kind.format for kind in call_signature)})'. at line {expression.line} in module '{self.module.name}'")

            fun = fun_signatures[signature_found]

            if type(fun) is FunctionDeclaration:
                expression.function_module = self.module
                expression.function_head = fun.head
            elif type(fun) is FunctionHead:
                expression.function_head = fun

            return fun.kind

        elif type(expression) is BinaryOperation:
            left_kind = self.check_expression(expression.left)
            right_kind = self.check_expression(expression.right)

            if left_kind != right_kind:
                raise TypeError(f"expression type mismatch, expecting '{left_kind.format}', found '{right_kind.format}'. {expression.format}. at line {expression.line} in module '{self.module.name}'")

            return left_kind
        elif type(expression) is Dot:
            if expression.left in self.module.enums:
                return Type(Name('int'))

            if expression.left not in self.module.variables:
                raise NameError(f"{expression.left.format} is undeclared. {expression.format}. at line {expression.line} in module '{self.module.name}'")
            
            let = self.module.variables[expression.left]
            let_kind = let if let.kind == Type(Name('type')) else let.kind

            if let_kind not in self.module.structs:
                raise NameError(f"can't access '{expression.format}', '{let.format}' is not a struct. at line {expression.line} in module '{self.module.name}'")
            
            struct = self.module.structs[let_kind]

            if expression.right.value not in struct.members:
                raise NameError(f"can't access '{expression.format}', it is not a valid struct '{struct.name.format}' field. at line {expression.line} in module '{self.module.name}'")
            
            return struct.members[expression.right]
        
        elif type(expression) is Item:
            kind = self.check_expression(expression.left)
            self.check_expression(expression.right.values[0])

            if kind != Type(Name('str')):
                raise TypeError(f"value of type {kind} is not indexable. at line {expression.line} in module '{self.module.name}'")

            return Type(Name('char'))
        elif type(expression) is Parenthesized:
            return self.check_expression(expression.expression)

        return expression.kind
    
    def check_extern(self, extern: Extern):
        if type(extern.head) is not FunctionHead:
            raise NotImplementedError(f"extern without fun is not implemented. in module '{self.module.name}'")

        if extern.head.name in self.module.functions:
            raise Exception(f"overriding extern functions is not supported. {extern.head.format}. at line {extern.head.line} in module '{self.module.name}'")

        self.module.functions.setdefault(extern.head.name, {})
        self.module.functions[extern.head.name][extern.head.signature] = extern

        return extern

    def check_body(self, body: Body):
        checker = Checker(body.lines, self.module)
        checker.check()

        return body
    
    def check_function_declaration(self, function_declaration: FunctionDeclaration):
        self.module.functions.setdefault(function_declaration.head.name, {})
        self.module.functions[function_declaration.head.name][function_declaration.head.signature] = function_declaration
        
        old_self_module = self.module
        self.module = self.module.copy()

        for parameter_name, parameter_kind in function_declaration.head.parameters.items():
            self.module.variables[parameter_name] = parameter_kind

        self.check_body(function_declaration.body)

        function_declaration.head.module = self.module
        self.module = old_self_module
        
        return function_declaration
    
    def check_while(self, while_: While):
        self.check_expression(while_.condition)
        self.check_body(while_.body)

        return while_

    def check_if(self, if_: If):
        self.check_expression(if_.condition)
        self.check_body(if_.body)

        return if_
    
    def check_else(self, else_: Else):
        self.check_body(else_.body)

        return else_
    
    def check_import(self, import_: Import):
        tokens = tuple(Lexer(Source(open(f'{import_.head.format.replace(".", "/")}.greek').read())))
        asts = tuple(Parser(Source(tokens), import_.head.format))
        checker = Checker(asts, Module.new(import_.head.format))
        module = checker.check()

        self.module.modules[import_.head.format] = module

        return import_
    
    def check_return(self, return_: Return):
        self.check_expression(return_.value)

        return return_
    
    def check_enum_declaration(self, enum_declaration: EnumDeclaration):
        if enum_declaration.name in self.module.enums:
            raise NameError(f"an enum with name {enum_declaration.name} already exists in this module. at line {enum_declaration.name.line} in module {self.module.name}")
            
        self.module.enums[enum_declaration.name] = enum_declaration

        return enum_declaration

    def check(self):
        for ast in self.asts:
            if type(ast) is StructDeclaration:
                self.check_struct_declaration(ast)
            elif type(ast) is EnumDeclaration:
                self.check_enum_declaration(ast)
            elif type(ast) is Import:
                self.check_import(ast)
            elif type(ast) is Extern:
                self.check_extern(ast)
            elif type(ast) is FunctionDeclaration:
                self.check_function_declaration(ast)
            elif type(ast) is Let:
                self.check_let(ast)
            elif type(ast) is Assignment:
                self.check_assignment(ast)
            elif type(ast) is While:
                self.check_while(ast)
            elif type(ast) is If:
                self.check_if(ast)
            elif type(ast) is Else:
                self.check_else(ast)
            elif type(ast) is Return:
                self.check_return(ast)
            else:
                self.check_expression(ast)
        
        return self.module