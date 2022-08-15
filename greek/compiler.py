from dataclasses import dataclass
from .checker import Scope, check_function
from .parser import Array, Ast, Add, Dot, Else, Item, ExternFunction, NotEqual, Return, Set, SetAdd, SetSub, SetMul, SetDiv, SetRem, Equal, GreaterThan, If, LessThan, Let, Struct, StructDeclaration, Sub, Mul, Div, Rem, Expression, Literal, Type, Name, Call, Function, Body, While

NEWLINE = '\n'

def _get_dot_bases(dotname: str):
    *basepath, basename = dotname.split('.')
    return '.'.join(basepath), basename

def pythontypes_to_greektypes(type: type):
    return Type({str: Name('str'), int: Name('int'), float: Name('float')}[type])

def resolve_call(scope: Scope, call: Call) -> Function:
    def resolve_signature(expression: Expression):
        if type(expression) is Call:
            return resolve_call(scope, expression).return_type

        elif type(expression) is Literal:
            return pythontypes_to_greektypes(type(expression.value))
        
        elif type(expression) is Name:
            if expression.value in scope.variables:
                return scope.variables[expression.value][0]
            elif expression.value in scope.constants:
                return scope.constants[expression.value][0]

            if Type(name=expression.value) in scope.types:
                return Type(Name('int'))
            
            raise NameError(f"unknown name {expression.value}")
        
        elif type(expression) is Item:
            signature = resolve_signature(expression.left)

            if signature.name.value == 'str':
                return Type(Name('char'))
            
            elif signature.name.value == 'list':
                if signature.subtype is None:
                    raise ValueError('type list requires a subtype')

                return signature.subtype
            
            raise NotImplementedError(f"can't translate type {signature}")
        
        elif type(expression) is Dot:
            if dot_call := expression.get_call:
                return resolve_call(scope, Call(expression.as_name, list(dot_call.arguments))).return_type

            signature = resolve_signature(expression.left)
            
            if signature.name.value == 'pointer':
                struct = scope.structs[signature.subtype]
            else:
                struct = scope.structs[signature]

            return struct.kinds[struct.names.index(expression.right)]

        elif type(expression) in (Add, Sub, Mul, Div, Rem):
            return resolve_signature(expression.left)
        
        return Type(Name('void'))
    
    call_signature = tuple(resolve_signature(argument) for argument in call.arguments)
    
    if '.' in call.name.value:
        module_path, function_name = _get_dot_bases(call.name.value)

        variable_kind = None
        variable_name = None
        
        if module_path in scope.variables:
            variable_kind = scope.variables[module_path][0]
            function = scope.types[variable_kind]
        elif Type(Name(module_path)) in scope.structs:
            function = scope.structs[Type(Name(module_path))]
        else:
            function = scope.modules[module_path]
        
        if function_name in function.functions:
            function = function.functions[function_name]
            
            if call_signature in function:
                function = function[call_signature]
            elif variable_kind and (method_call_signature := (variable_kind, *call_signature)) in function:
                function = function[method_call_signature]
            else:
                raise NameError(f"there is no function named '{function_name}' in module '{module_path}' with signature {call_signature}'")
        else:
            raise NameError(f"there is no function named '{function_name}' in module '{module_path}'")
    else:
        function_name = call.name.value
        function = scope.functions[function_name]
        
        if function_name not in scope.functions:
            raise NameError(f"there is no function named '{function_name}'")

        if call_signature in function:
            function = function[call_signature]
        else:
            raise ValueError(f"can't find a function named '{function_name}' with signature {call_signature}")
    
    return function

def compile_call(scope: Scope, call: Call, direct=False):
    function = resolve_call(scope, call)

    if direct:
        if type(function) is not ExternFunction:
            if function.owner is not None:
                return f'{function.owner.kind.as_name.value}({", ".join(compile_expression(scope, argument) for argument in call.arguments)})'
    
            return f'{scope.name.value.replace(".", "__")}__{function.name.value}({", ".join(compile_expression(scope, argument) for argument in call.arguments)})'
        
    if type(function) is not ExternFunction and function.owner is not None:
        call_module, _ = _get_dot_bases(call.name.value)
        
        if Name("self") in function.parameters and Type(Name(call_module)) not in scope.structs:
            compiled_expressions = (call_module.replace(".", "__"), *(compile_expression(scope, argument) for argument in call.arguments[1:]))
        else:
            compiled_expressions = tuple(compile_expression(scope, argument) for argument in call.arguments)

        return f'{function.owner.kind.as_name.value}__{function.name.value}({", ".join(compiled_expressions)})'

    if direct:
        return f'{function.name.value}({", ".join(compile_expression(scope, argument) for argument in call.arguments)})'
    
    return f'{_get_dot_bases(call.name.value)[0].replace(".", "__")}__{function.name.value}({", ".join(compile_expression(scope, argument) for argument in call.arguments)})'

def compile_expression(scope: Scope, expression: Expression):
    if type(expression) is Name:
        if Type(expression) in scope.structs:
            return f'sizeof({expression.value})'

        return expression.value

    if type(expression) is Struct:
        return f'({compile_type(scope, expression.kind)}) {{{", ".join(compile_expression(scope, field) for field in expression.fields)}}}'
    elif type(expression) is Call:
        return compile_call(scope, expression, True)
    elif type(expression) is Add:
        return f'{compile_expression(scope, expression.left)} + {compile_expression(scope, expression.right)}'
    elif type(expression) is Sub:
        return f'{compile_expression(scope, expression.left)} - {compile_expression(scope, expression.right)}'
    elif type(expression) is Mul:
        return f'{compile_expression(scope, expression.left)} * {compile_expression(scope, expression.right)}'
    elif type(expression) is Div:
        return f'{compile_expression(scope, expression.left)} / {compile_expression(scope, expression.right)}'
    elif type(expression) is Rem:
        return f'{compile_expression(scope, expression.left)} % {compile_expression(scope, expression.right)}'
    
    elif type(expression) is NotEqual:
        return f'{compile_expression(scope, expression.left)} != {compile_expression(scope, expression.right)}'
    elif type(expression) is Equal:
        return f'{compile_expression(scope, expression.left)} == {compile_expression(scope, expression.right)}'
    elif type(expression) is LessThan:
        return f'{compile_expression(scope, expression.left)} < {compile_expression(scope, expression.right)}'
    elif type(expression) is GreaterThan:
        return f'{compile_expression(scope, expression.left)} > {compile_expression(scope, expression.right)}'

    elif type(expression) is Literal:
        return f'"{expression.value}"' if type(expression.value) is str else str(expression.value)
    
    elif type(expression) is Array:
        return f'{{{", ".join(compile_expression(scope, item) for item in expression.items)}}}'

    elif type(expression) is Dot:
        if dot_call := expression.get_call:
            dot_call = Call(expression.as_name, list(dot_call.arguments))
            return f'{compile_call(scope, dot_call)}'
        
        if expression.left in scope.variables:
            if scope.variables[expression.left][0].name.value == "pointer":
                return expression.as_name.value.replace('.', '->')

        return expression.as_name.value

    elif type(expression) is Item:
        return f'{compile_expression(scope, expression.left)}[{compile_expression(scope, expression.right)}]'

    return str(expression)

def compile_type(scope: Scope, type_: Type | Name):
    if type(type_) is Name:
        return type_.value

    if type_.subtype is None:
        return type_.name.value
    
    if type_.name.value == "pointer":
        return f'{compile_type(scope, type_.subtype)}*'

    return f'{type_.name.value}_{compile_type(scope, type_.subtype)}'

def compile_let(scope: Scope, declaration: Let):
    compiled_type = compile_type(scope, declaration.kind)

    if declaration.kind.name.value == "list":
        return f'{compile_type(scope, declaration.kind.subtype)} {declaration.name.value}[] = {compile_expression(scope, declaration.value)}'
    
    return f'{compiled_type} {declaration.name.value} = {compile_expression(scope, declaration.value)}'

def compile_set(scope: Scope, set: Set):
    if type(set) is SetAdd:
        return f'{set.name.value} += {compile_expression(scope, set.value)}'
    elif type(set) is SetSub:
        return f'{set.name.value} -= {compile_expression(scope, set.value)}'
    elif type(set) is SetMul:
        return f'{set.name.value} *= {compile_expression(scope, set.value)}'
    elif type(set) is SetDiv:
        return f'{set.name.value} /= {compile_expression(scope, set.value)}'
    elif type(set) is SetRem:
        return f'{set.name.value} %= {compile_expression(scope, set.value)}'

    return f'{compile_expression(scope, set.name)} = {compile_expression(scope, set.value)}'

def compile_if(scope: Scope, statement: If):
    return f'if ({compile_expression(scope, statement.condition)}) {compile_body(scope, statement.body)}'

def compile_else(scope: Scope, statement: Else):
    return f'else {compile_body(scope, statement.body)}'

def compile_while(scope: Scope, loop: While):
    return f'while ({compile_expression(scope, loop.condition)}) {compile_body(scope, loop.body)}'

def compile_return(scope: Scope, return_: While):
    return f'return {compile_expression(scope, return_.value)};'

def compile_body(scope: Scope, body: Body):
    INDENT = '\n' + ('  ' * scope.indent)
    INDENT1 = '\n' + ('  ' * (1 + scope.indent))

    def compile(line: Expression):
        if type(line) is Let:
            return f'{compile_let(scope.copy(), line)};'
        elif type(line) in (Set, SetAdd, SetSub, SetMul, SetDiv, SetRem):
            return f'{compile_set(scope.copy(), line)};'
        
        elif type(line) is If:
            return compile_if(scope.copy(), line)
        elif type(line) is Else:
            return compile_else(scope.copy(), line)
        elif type(line) is While:
            return compile_while(scope.copy(), line)
        elif type(line) is Return:
            return compile_return(scope, line)

        return f'{compile_expression(scope, line)};'

    compiled_lines = INDENT1.join(compile(line) for line in body.lines)

    return f'{INDENT}{{{INDENT1}{compiled_lines}{INDENT}}}'

def compile_function(scope: Scope, function: Function):
    INDENT = '\n' + ('  ' * scope.indent)
    compiled_parameters = ", ".join(f'{kind.name.value} {parameter.value}' for parameter, kind in function.parameters.items())
    
    if type(function) is ExternFunction:
        return f'// {function.return_type.name.value} {function.name.value}({compiled_parameters});'

    if function.name.value == "main":
        return f'{INDENT}{compile_type(scope, function.return_type)} {function.name.value}({compiled_parameters}){compile_body(scope, function.body)}'
    
    if function.owner is not None:
        return f'{INDENT}{compile_type(scope, function.return_type)} {function.owner.kind.as_name.value.replace("@", "_")}__{function.name.value}({compiled_parameters}){compile_body(scope, function.body)}'

    return f'{INDENT}{compile_type(scope, function.return_type)} {scope.name.value.replace(".", "__")}__{function.name.value}({compiled_parameters}){compile_body(scope, function.body)}'

def compile_struct(scope: Scope, struct: StructDeclaration):
    compiled_struct_body = ' '.join(f'{compile_type(scope, kind)} {name.value};' for name, kind in zip(struct.names, struct.kinds))
    struct_functions = []

    scope = scope.copy()
    
    for signatures in struct.functions.values():
        for function in signatures.values():
            struct_functions.append(check_function(scope, function))

    return f'typedef struct {{ {compiled_struct_body} }} {compile_type(scope, struct.kind)};{NEWLINE}{NEWLINE.join(compile_function(scope, function) for function in struct_functions)}'

@dataclass
class Compilation:
    compiled_functions: set[Name]
    compiled_modules: set[Name]

    @classmethod
    def new(cls):
        return cls(set(), set())

def compile(compilation: Compilation, scope: Scope, step=0):
    if step == 0:
        yield '#define _CRT_SECURE_NO_WARNINGS'
        yield '#define _CRT_NONSTDC_NO_DEPRECATE'
        
        yield '#include <stdbool.h>'
        yield '#include <malloc.h>'
        yield '#include <memory.h>'
        yield '#include <stdlib.h>'
        yield '#include <stdio.h>'

        yield '#define str char*'
        yield '#define voidptr void*'
        yield '#define function void*'
        yield '#define list_string char'
    
    for name, value in scope.constants.items():
        yield f'#define {name.value} {compile_expression(scope, value[1])}'

    for module in scope.modules.values():
        if type(module) is Scope and module.name not in compilation.compiled_modules:
            compilation.compiled_modules |= {module.name}
            yield from compile(compilation, module, step + 1)

    for struct in scope.structs.values():
        yield compile_struct(scope, struct)

    for signatures in scope.functions.values():
        for signature, function in signatures.items():
            if len(signatures) > 1 and type(function) is Function:
                function.name = Name(f'{function.name.value.replace("_", "__")}_{"_".join(kind.name.value for kind in signature)}')

            yield compile_function(scope, function)
    
    for name in scope.constants.keys():
        yield f'#undef {name.value}'
    
    return
