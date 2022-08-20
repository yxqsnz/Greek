from dataclasses import dataclass
from .lexer import Literal, Name, Type
from .parser import Assignment, Ast, BinaryOperation, Body, Call, Dot, Else, EnumDeclaration, Expression, Extern, FunctionDeclaration, FunctionHead, If, Item, Let, Parenthesized, Return, Struct, StructDeclaration, While
from .checker import Module

NEWLINE = '\n'
SOFTTAB = '  '

@dataclass
class Compilation:
    compiled_modules: list[Module]

    @classmethod
    def new(cls):
        return cls(list())

class Compiler:
    def __init__(self, module: Module, compilation: Compilation):
        self.module = module
        self.compilation = compilation
    
    def __iter__(self):
        return self.compile()
    
    def compile_expression(self, expression: Expression):
        expression_cls = type(expression)

        if expression_cls is Name or expression_cls is Type:
            return expression.format
        elif expression_cls is Literal:
            if expression.kind == Name('str'):
                return f'"{expression.value}"'
            
            return expression.format
        elif expression_cls is Parenthesized:
            return f'({self.compile_expression(expression.expression)})'
        elif expression_cls is Dot:
            if expression.left.format in self.module.variables:
                return expression.format

            return f'{expression.format.replace(".", "_")}'
        elif expression_cls is Item:
            if expression.right.values[0].kind == Name('type'):
                compiled_right = "_".join(self.compile_expression(value) for value in expression.right.values)
                
                return f'{expression.left.format}___{compiled_right}'

            return f'{expression.left.format}[{self.compile_expression(expression.right.values[0])}]'

        if expression_cls is BinaryOperation:
            return f'{self.compile_expression(expression.left)} {expression.operator.value} {self.compile_expression(expression.right)}'
        elif expression_cls is Call:
            return self.compile_call(expression)
        elif expression_cls is Struct:
            return f'({expression.kind.format}) {{ {", ".join(self.compile_expression(value) for value in expression.values)} }}'

        return str(expression)
    
    def compile_call(self, call: Call):
        if call.function_head and call.function_head.struct:
            if call.function_head.struct.name != call.head.left:
                call.arguments = [call.head.left, *call.arguments]

        compiled_body = ", ".join(self.compile_expression(argument) for argument in call.arguments)
            
        if call.function_head is None:
            compiled_signature = ""
        else:
            compiled_signature = "_".join(self.compile_expression(kind) for kind in call.function_head.signature)
            compiled_signature = "__" + compiled_signature if compiled_signature else ""
        
        if call.function_module is not None and type(call.head) is not Dot:
            mangled_prefix = call.function_module.name.replace(".", "_") + '_'
        else:
            mangled_prefix = ""
        
        if call.function_head and call.function_head.struct:
            return f'{mangled_prefix}{call.function_head.struct.name.format}_{call.function_head.name.format}{compiled_signature}({compiled_body})'
        
        return f'{mangled_prefix}{self.compile_expression(call.head).replace(".", "_")}{compiled_signature}({compiled_body})'

    
    def compile_body(self, body: Body, indent=0):
        INDENT = (SOFTTAB * indent)
        INDENT1 = (SOFTTAB * (indent +1))

        def compile(line: Ast):
            if type(line) is Return:
                return f'return {self.compile_expression(line.value)};'
            elif type(line) is Let:
                return f'{line.kind.format} {line.name.format} = {self.compile_expression(line.value)};'
            elif type(line) is If:
                return f'if ({self.compile_expression(line.condition)}){self.compile_body(line.body, indent +1)}'
            elif type(line) is Else:
                return f'else {self.compile_body(line.body, indent +1)}'
            elif type(line) is While:
                return f'while ({self.compile_expression(line.condition)}){self.compile_body(line.body, indent +1)}'
            elif type(line) is Assignment:
                return f'{self.compile_expression(line.head)} {line.operator.value} {self.compile_expression(line.value)};'

            return self.compile_expression(line) + ';'

        return f'{NEWLINE}{INDENT}{{{NEWLINE}{NEWLINE.join(INDENT1 + compile(line) for line in body.lines)}{NEWLINE}{INDENT}}}'
    
    def compile_function(self, function: FunctionDeclaration | FunctionHead | Extern):
        old_module = self.module

        if function.module is not None:
            self.module = function.module

        compiled_parameters = ", ".join(f"{self.compile_expression(parameter.value)} {name.value}" for name, parameter in function.head.parameters.items())
        mangled_prefix = "_".join(self.module.name.split('.'))
        compiled_signature = "_".join(self.compile_expression(kind) for kind in function.head.signature)
        compiled_signature = "__" + compiled_signature if compiled_signature else ""

        if type(function) is FunctionDeclaration:
            if function.head.name == "main":
                result = f'{self.compile_expression(function.kind)} {function.head.name.value}({compiled_parameters}){self.compile_body(function.body)}'
            else:
                result = f'{self.compile_expression(function.kind)} {mangled_prefix}_{function.head.name.value}{compiled_signature}({compiled_parameters}){self.compile_body(function.body)}'
        else:
            result = f'// {self.compile_expression(function.kind)} {function.head.name.value}({compiled_parameters});'
        
        self.module = old_module

        return result
    
    def compile_struct_declaration(self, struct_declaration: StructDeclaration):
        old_self_module = self.module
        self.module = self.module.copy()
        self.module.name = struct_declaration.name.format

        compiled_struct_body = " ".join(f"{member_kind.format} {member_name.format};" for member_name, member_kind in struct_declaration.members.items())
        compiled_methods = []

        for signatures in struct_declaration.methods.values():
            for method in signatures.values():
                self.module.variables |= method.head.module.variables

                compiled_methods.append(self.compile_function(method))
        
        result = f'typedef struct {{ {compiled_struct_body} }} {struct_declaration.name.format}; {NEWLINE}{NEWLINE.join(compiled_methods)}'

        self.module = old_self_module

        return result
    
    def compile_enum_declaration(self, enum_declaration: EnumDeclaration):
        compiled_enum_body = ", ".join(f"{enum_declaration.name.format}_{member.format}" for member in enum_declaration.members)

        return f'typedef enum {{ {compiled_enum_body} }} {enum_declaration.name.format};'

    def compile(self):
        self.compilation.compiled_modules.append(self.module.name)

        for module in self.module.modules.values():
            if module.name in self.compilation.compiled_modules:
                continue

            print('entering module', module.name)

            compiler = Compiler(module, self.compilation)
            yield from compiler
        
        for let in self.module.variables.values():
            if let.kind == Type(Name('str')):  
                yield f'#define {let.name.format} "{let.value.value}"'
            else:
                yield f'#define {let.name.format} {self.compile_expression(let.value.format)}'
        
        for enum_declarations in self.module.enums.values():
            yield self.compile_enum_declaration(enum_declarations)

        for struct_declarations in self.module.structs.values():
            yield self.compile_struct_declaration(struct_declarations)

        for signatures_and_functions in self.module.functions.values():
            for function in signatures_and_functions.values():
                yield self.compile_function(function)
        
        return