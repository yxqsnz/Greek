from dataclasses import dataclass

from .lexer import Token, Keyword, Literal, Comment, Name
from .control import Control

@dataclass
class Type:
    name: Name
    subtype: Name=None

    def __hash__(self):
        return hash(self.name)
    
    @property
    def as_name(self) -> Name:
        if self.subtype is None:
            return self.name
            
        if type(self.subtype) is Type:
            return Name(f'{self.name.value}@{self.subtype.as_name.value}')
        
        return Name(f'{self.name.value}@{self.subtype.value}')

@dataclass
class Call:
    name: Name
    arguments: list["Expression"]

@dataclass
class Not:
    expression: "Expression"

@dataclass
class Add:
    left: "Expression"
    right: "Expression"

class Sub(Add): pass
class Mul(Add): pass
class Div(Add): pass
class Rem(Add): pass

class NotEqual(Add): pass
class Equal(Add): pass
class LessThan(Add): pass
class GreaterThan(Add): pass
class LessThanEqual(Add): pass
class GreaterThanEqual(Add): pass

class Item(Add): pass

class Dot(Add):
    @property
    def as_name(self) -> Name:
        if type(self.right) is Dot: 
            return Name(f'{self.left.value}.{self.right.as_name.value}')
        elif type(self.right) is Call:
            return Name(f'{self.left.value}.{self.right.name.value}')

        return Name(f'{self.left.value}.{self.right.value}')
    
    @property
    def get_call(self):
        if type(self.right) is Call:
            return self.right
        elif type(self.right) is Dot:
            return self.right.get_call
        
        return

Expression = Call | Add

@dataclass
class Body:
    lines: list[Expression]

@dataclass
class Let:
    name: Name
    kind: Name
    value: Expression

@dataclass
class Set:
    name: Name
    value: Expression

class SetAdd(Set): pass
class SetSub(Set): pass
class SetMul(Set): pass
class SetDiv(Set): pass
class SetRem(Set): pass

@dataclass
class Import:
    name: Expression

    @property
    def as_path(self):
        if type(self.name) is Dot:
            return self.name.as_name
        
        return self.name

@dataclass
class Return:
    value: Expression

@dataclass
class ExternFunction:
    name: Name
    parameters: dict[Name, Name]
    return_type: Name

@dataclass
class Function:
    name: Name
    return_type: Name
    parameters: dict[Name, Name]
    body: Body
    owner=None

    @property
    def signature(self):
        return tuple(self.parameters.values())

@dataclass
class If:
    condition: Expression
    body: Body
    
class While(If): pass

@dataclass
class Else:
    body: Body

@dataclass
class Array:
    items: list[Expression]

@dataclass
class StructDeclaration:
    kind: Type
    names: list[Name]
    kinds: list[Type]
    functions: dict[Name, dict[tuple[Name], Function]]

@dataclass
class Struct:
    kind: Type
    fields: list[Expression]

Ast = Function | Let | Body | Add | Call

@dataclass
class Parsing:
    line: int=0

def parse_call(parsing: Parsing, seeker: Control, name: Name) -> Call:
    arguments = []

    for token in seeker:
        if token is Token.RightParenthesis:
            break
        elif token is Token.Comma:
            continue
        else:
            expression = parse_expression(parsing, seeker, token, {Token.Comma, Token.RightParenthesis})

            if expression:
                arguments.append(expression)

    return Call(name, arguments)

def parse_array(parsing: Parsing, seeker: Control) -> Array:
    items = []

    for token in seeker:
        if token is Token.RightBracket:
            break
        elif token is Token.Comma:
            continue

        expression = parse_expression(parsing, seeker, token, {Token.Comma})

        if expression is not None:
            items.append(expression)

    return Array(items)

def parse_struct(parsing: Parsing, seeker: Control, kind: Type) -> Struct:
    fields = []

    for token in seeker:
        if token is Token.RightBrace:
            break
        elif token is Token.Comma:
            continue
        elif token is Token.Line:
            parsing.line += 1
            continue

        expression = parse_expression(parsing, seeker, token)

        if expression is not None:
            fields.append(expression)

    return Struct(kind, fields)

def parse_parenthesized_expression(parsing: Parsing, seeker: Control, value: Expression, ignore=set()):
    expression = parse_expression(parsing, seeker, value, ignore | {Token.RightParenthesis})

    if (token := seeker.take()) is not Token.RightParenthesis:
        raise SyntaxError(f"expected ')'. found {token}")
    
    return expression

def parse_expression(parsing: Parsing, seeker: Control, value: Expression, ignore=set()) -> Name:
    if value is Token.LeftBracket:
        return parse_expression(parsing, seeker, parse_array(seeker))
    elif value is Token.LeftParenthesis:
        return parse_expression(parsing, seeker, parse_parenthesized_expression(parsing, seeker, seeker.take(), ignore))
    elif value is Token.Not:
        return parse_expression(parsing, seeker, Not(parse_expression(parsing, seeker, seeker.take(), ignore)), ignore)

    token = seeker.take()

    if token in ignore:
        pass

    elif token is Token.LeftParenthesis:
        return parse_expression(parsing, seeker, parse_call(parsing, seeker, value))
    elif type(value) is Name and token is Token.At:
        seeker.drop()
        return parse_expression(parsing, seeker, parse_type(parsing, seeker, value))
    
    elif type(value) in (Type, Name) and token is Token.LeftBrace:
        return parse_expression(parsing, seeker, parse_struct(parsing, seeker, value))
    
    elif token is Token.Plus:
        return parse_expression(parsing, seeker, Add(value, parse_expression(parsing, seeker, seeker.take(), {Token.EqualEqual})), ignore)
    elif token is Token.Minus:
        return parse_expression(parsing, seeker, Sub(value, parse_expression(parsing, seeker, seeker.take(), {Token.EqualEqual})), ignore)
    elif token is Token.Star:
        return parse_expression(parsing, seeker, Mul(value, parse_expression(parsing, seeker, seeker.take(), {Token.EqualEqual})), ignore)
    elif token is Token.Slash:
        return parse_expression(parsing, seeker, Div(value, parse_expression(parsing, seeker, seeker.take(), {Token.EqualEqual})), ignore)
    elif token is Token.Percent:
        return parse_expression(parsing, seeker, Rem(value, parse_expression(parsing, seeker, seeker.take(), {Token.EqualEqual})), ignore)
    
    elif token is Token.NotEqual:
        return NotEqual(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))
    elif token is Token.EqualEqual:
        return Equal(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))
    elif token is Token.LessThan:
        return LessThan(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))
    elif token is Token.GreaterThan:
        return GreaterThan(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))
    elif token is Token.LessThanEqual:
        return LessThanEqual(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))
    elif token is Token.GreaterThanEqual:
        return GreaterThanEqual(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))
    
    elif token is Token.Dot:
        return parse_expression(parsing, seeker, Dot(value, parse_expression(parsing, seeker, seeker.take(), {Token.Plus, Token.Minus, Token.Star, Token.Slash, Token.Percent, Token.EqualEqual, Token.LeftParenthesis})), ignore)
    
    elif type(value) in (Name, Dot) and token is Token.LeftBracket:
        item = Item(value, parse_expression(parsing, seeker, seeker.take(), ignore=ignore))

        if (token := seeker.take()) is not Token.RightBracket:
            raise SyntaxError(f"expected ']'. found {token}")

        return parse_expression(parsing, seeker, item, ignore)

    seeker.drop()

    return value

def parse_else(parsing: Parsing, seeker: Control) -> Else:
    return Else(parse_body(parsing, seeker))

def parse_if(parsing: Parsing, seeker: Control) -> If:
    return If(parse_expression(parsing, seeker, seeker.take(), {Token.LeftBrace}), parse_body(parsing, seeker))

def parse_while(parsing: Parsing, seeker: Control) -> While:
    return While(parse_expression(parsing, seeker, seeker.take(), {Token.LeftBrace}), parse_body(parsing, seeker))

def parse_return(parsing: Parsing, seeker: Control) -> Return:
    return Return(parse_expression(parsing, seeker, seeker.take()))

def parse_body(parsing: Parsing, seeker: Control) -> Body:
    if (token := seeker.take()) is not Token.LeftBrace:
        raise SyntaxError(f"expecting '{{', found {token}. at {parsing.line}")
    
    lines = []

    for token in seeker:
        if token is Token.RightBrace:
            break
        elif token is Token.Line:
            parsing.line += 1
            continue

        if token is Keyword.Let:
            lines.append(parse_let(parsing, seeker, seeker.take()))
        elif token is Keyword.If:
            lines.append(parse_if(parsing, seeker))
        elif token is Keyword.Else:
            lines.append(parse_else(parsing, seeker))
        elif token is Keyword.While:
            lines.append(parse_while(parsing, seeker))
        elif token is Keyword.Return:
            lines.append(parse_return(parsing, seeker))
        
        else:
            name = parse_expression(parsing, seeker, token)
            token = seeker.take()

            if token is Token.Equal:
                lines.append(Set(name, parse_expression(parsing, seeker, seeker.take())))
            elif token is Token.PlusEqual:
                lines.append(SetAdd(name, parse_expression(parsing, seeker, seeker.take())))
            elif token is Token.MinusEqual:
                lines.append(SetSub(name, parse_expression(parsing, seeker, seeker.take())))
            elif token is Token.StarEqual:
                lines.append(SetMul(name, parse_expression(parsing, seeker, seeker.take())))
            elif token is Token.SlashEqual:
                lines.append(SetDiv(name, parse_expression(parsing, seeker, seeker.take())))
            elif token is Token.PercentEqual:
                lines.append(SetRem(name, parse_expression(parsing, seeker, seeker.take())))
            else:
                seeker.drop()

                expression = parse_expression(parsing, seeker, name)

                if expression:
                    lines.append(expression)
    
    return Body(lines)

def parse_type(parsing: Parsing, seeker: Control, name: Name) -> Type:
    if type(name) is not Name:
        raise SyntaxError(f"expecting Name, found {name}. at line {parsing.line}")
    
    token = seeker.take()

    if token is Token.At:
        subname = seeker.take()

        if type(subname) is Name:
            subtype = parse_type(parsing, seeker, subname)
        else:
            raise SyntaxError

        return Type(name, subtype)
    else:
        seeker.drop()
    
    return Type(name)

def parse_let(parsing: Parsing, seeker: Control, name: Name) -> Let:
    if (took := seeker.take()) is not Token.Colon:
        raise SyntaxError(f"expecting ':' after let {name}, found {took}. at line {parsing.line}")
    
    kind = parse_type(parsing, seeker, seeker.take())

    if (token := seeker.take()) is not Token.Equal:
        raise SyntaxError(f"expecting '=' found {token}. at {name} variable declaration")

    return Let(name, kind, parse_expression(parsing, seeker, seeker.take()))

def parse_extern_function(parsing: Parsing, seeker: Control, name: Name) -> Function:
    if seeker.take() is not Token.LeftParenthesis:
        raise SyntaxError(f"expecting '('. at function {name} head")
    
    parameters = {}

    for token in seeker:
        if token is Token.RightParenthesis:
            break
        elif token is Token.Comma:
            continue
        
        if type(token) is Name:
            if (took := seeker.take()) is not Token.Colon:
                raise SyntaxError(f"expecting ':' after function parameter {token}. found {took}")

            parameter_type = parse_type(parsing, seeker, seeker.take())
            parameters[token] = parameter_type
        else:
            raise SyntaxError(f"expecting ',' or ')'. at {name} head")
    
    return_type = parse_type(parsing, seeker, seeker.take())

    return ExternFunction(name, parameters, return_type)

def parse_import(parsing: Parsing, seeker: Control) -> Import:
    return Import(parse_expression(parsing, seeker, seeker.take()))

def parse_function(parsing: Parsing, seeker: Control, name: Name) -> Function:
    if seeker.take() is not Token.LeftParenthesis:
        raise SyntaxError(f"expecting '('. at function {name} head")
    
    parameters = {}

    for token in seeker:
        if token is Token.RightParenthesis:
            break
        elif token is Token.Comma:
            continue
        
        if type(token) is Name:
            if (took := seeker.take()) is not Token.Colon:
                raise SyntaxError(f"expecting ':' after function parameter {token}. found {took}")

            parameter_type = parse_type(parsing, seeker, seeker.take())
            parameters[token] = parameter_type            
        else:
            raise SyntaxError(f"expecting ',' or ')'. at {name} head")
    
    return_type = parse_type(parsing, seeker, seeker.take())

    return Function(name, return_type, parameters, parse_body(parsing, seeker))

def parse_struct_declaration(parsing: Parsing, seeker: Control, kind: Type) -> StructDeclaration:
    if seeker.take() is not Token.LeftBrace:
        raise SyntaxError
    
    names = []
    kinds = []
    functions = dict()

    for token in seeker:
        if token is Token.Line:
            parsing.line += 1
            continue

        if token is Token.RightBrace:
            break

        elif type(token) is Name:
            names.append(token)

            if (took := seeker.take()) is not Token.Colon:
                raise SyntaxError(f"expecting ':' after struct member {token}. found {took}")
            
            kinds.append(parse_type(parsing, seeker, seeker.take()))
        
        elif token is Keyword.Fun:
            function = parse_function(parsing, seeker, seeker.take())

            functions.setdefault(function.name, {})
            functions[function.name][function.signature] = function

            names.append(function.name)
            kinds.append(Type(Name('function')))
        else:
            raise SyntaxError(f'{token} is not a Name')

    return StructDeclaration(kind, names, kinds, functions)

def parse(seeker: Control):
    parsing = Parsing()

    for token in seeker:
        if token is Token.EndOfFile:
            break
        elif token is Token.Line:
            parsing.line += 1
            continue

        if token is Keyword.Import:
            yield parse_import(parsing, seeker)
        elif token is Keyword.Fun:
            yield parse_function(parsing, seeker, seeker.take())
        
        elif token is Keyword.Extern:
            if seeker.take() is Keyword.Fun:
                yield parse_extern_function(parsing, seeker, seeker.take())
            else:
                raise NotImplementedError(f"'extern' without 'fun' is not implemented. at line {parsing.line}")
        
        elif token is Keyword.Struct:
            yield parse_struct_declaration(parsing, seeker, parse_type(parsing, seeker, seeker.take()))
        
        elif token is Keyword.Let:
            yield parse_let(parsing, seeker, seeker.take())

        elif type(token) is Comment:
            yield token
        else:
            raise NotImplementedError(token)

    return
