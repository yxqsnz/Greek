from ast import arguments
from dataclasses import dataclass
from typing import TYPE_CHECKING
from .lexer import Token, Keyword, Name, Type
from .source import Source

@dataclass
class BinaryOperation:
    left: "Expression"
    operator: Token
    right: "Expression"

    @property
    def line(self):
        return self.left.line
    
    @property
    def kind(self):
        return self.left.kind
    
    @property
    def format(self):
        return f'{self.left.format} {self.operator.value} {self.right.format}'

@dataclass
class Dot:
    left: "Expression"
    right: "Expression"

    @property
    def line(self):
        return self.left.line
    
    @property
    def format(self):
        return f'{self.left.format}.{self.right.format}'

if TYPE_CHECKING:
    from .checker import Module

@dataclass(eq=False, repr=False) # caution: enabling repr could lead to recursion
class Call:
    head: "Expression"
    arguments: list["Expression"]
    function_head: "FunctionHead"=None
    function_module: "Module"=None

    def __repr__(self):
        return f'Call(head={self.head}, arguments={self.arguments})'

    @property
    def line(self):
        return self.head.line
    
    @property
    def format(self):
        return f'{self.head.format}(...)'

@dataclass(eq=False)
class Item:
    left: "Expression"
    right: list["Expression"]

    def __hash__(self):
        return hash(self.left)
    
    def __eq__(self, value: "Expression"):
        return self.value == value

    @property
    def line(self):
        return self.left.line
    
    @property
    def format(self):
        return f'{self.left.format}{self.right.format}'
    
    @property
    def value(self):
        return self.left.value

@dataclass
class Parenthesized:
    expression: "Expression"

    @property
    def line(self):
        return self.expression.line
    
    @property
    def format(self):
        return f'({self.expression.format})'

Expression = Name | BinaryOperation | Call | Item | Parenthesized

@dataclass
class Import:
    head: Expression
    feet: Expression=None

@dataclass
class Return:
    value: Expression
    
    @property
    def kind(self):
        return self.value.kind
    
    @property
    def format(self):
        return f'return {self.value.format}'
    

@dataclass
class Extern:
    head: Expression

    def __hash__(self):
        return hash(self.head)

    @property
    def kind(self):
        return self.head.kind
    
    @property
    def name(self):
        return self.head.name

    @property
    def module(self):
        return self.head.module

@dataclass
class EnumDeclaration:
    name: Name
    members: list[Name]

@dataclass
class StructDeclaration:
    name: Name
    members: dict[Name, Expression]
    methods: dict[Name, "FunctionDeclaration"]

    @property
    def line(self):
        return self.name.line
    
    @property
    def format(self):
        return f'struct {self.name.format} {{ ... }}'

@dataclass
class Struct:
    name: Name
    values: list[Expression]

    @property
    def line(self):
        return self.name.line

    @property
    def kind(self):
        return self.name

@dataclass
class Array:
    values: list[Expression]

    @property
    def kind(self):
        if self.values:
            return Item(Name('array'), Array(values=[self.values[0].kind]))

        return Item(Name('array'), Array(values=[Name('any')]))
    
    @property
    def format(self):
        return f'[{", ".join(value.format for value in self.values)}]'

@dataclass
class Let:
    name: Type
    kind: Expression
    value: Expression
    
    @property
    def line(self):
        return self.name.line
    
    @property
    def format(self):
        return f'let {self.name.format}: {self.kind.format} = ...'

@dataclass
class Assignment:
    head: Expression
    value: Expression
    operator: Token

    @property
    def line(self):
        return self.head.line

@dataclass
class Body:
    lines: list[Expression]

    @property
    def line(self):
        if len(self.lines):
            return self.lines[0].line

        return 0

@dataclass(repr=False) # caution: enabling repr could lead to recursion
class FunctionHead:
    name: Type
    kind: Expression
    parameters: dict[Name, Expression]
    module: "Module"=None
    struct: "StructDeclaration"=None

    def __hash__(self):
        return hash((self.name, self.signature, self.kind))
    
    def __repr__(self):
        return f'FunctionHead(name={self.name!r}, kind={self.kind!r}, parameters={self.parameters!r})'

    @property
    def signature(self):
        return tuple(parameter for parameter in self.parameters.values())

    @property
    def line(self):
        return self.name.line
    
    @property
    def format(self):
        return f'fun {self.name.format}(...) {self.kind.format}'

@dataclass
class FunctionDeclaration:
    head: FunctionHead
    body: Body

    def __hash__(self):
        return hash(self.head)

    @property
    def line(self):
        return self.name.line
    
    @property
    def kind(self):
        return self.head.kind
    
    @property
    def name(self):
        return self.head.name

    @property
    def module(self):
        return self.head.module

@dataclass
class While:
    condition: Expression
    body: Body

    @property
    def line(self):
        return self.condition.line

@dataclass
class If:
    condition: Expression
    body: Body

    @property
    def line(self):
        return self.condition.line

@dataclass
class Else:
    body: Body

    @property
    def line(self):
        return self.body.line

Ast = Import | EnumDeclaration | StructDeclaration | FunctionDeclaration | Let

class Parser:
    def __init__(self, source: Source, filename="main", line=1):
        self.source = source
        self.filename = filename
        self.line = line
    
    def __iter__(self):
        return self.parse()

    def parse_call(self, head: Expression):
        arguments = []

        for token in self.source:
            if token is Token.EndOfFile:
                raise SyntaxError(f"unclosed function call '{head}'. at line {head.line}")
            elif token is Token.RightParenthesis:
                break

            argument = self.parse_expression(token, {Token.Comma, Token.RightParenthesis})
            
            if argument:
                arguments.append(argument)

            token = self.source.look()

            if token is Token.Comma:
                continue
            elif token is Token.RightParenthesis:
                break
            elif token is Token.EndOfFile:
                raise SyntaxError(f"unclosed function call '{head}'. at line {head.line}")
            else:
                raise SyntaxError(f"expecting ',' or ')' after function call argument {len(arguments)} for '{head.format}'. found {token}. at line {head.line}")

        return Call(head, arguments)
    
    def parse_array(self, left_bracket: Token):
        values = []

        for token in self.source:
            if token is Token.EndOfFile:
                raise SyntaxError(f"unclosed array literal '{left_bracket}'. at line {left_bracket.line}")
            elif token is Token.RightBracket:
                break

            value = self.parse_expression(token, {Token.Comma, Token.RightBracket})
            
            if value:
                values.append(value)

            token = self.source.look()

            if token is Token.Comma:
                continue
            elif token is Token.RightBracket:
                break
            elif token is Token.EndOfFile:
                raise SyntaxError(f"unclosed array literal '{left_bracket}'. at line {left_bracket.line}")
            else:
                raise SyntaxError(f"expecting ',' or ')' after function call argument. at line {token.line}")

        return Array(values)

    def parse_expression(self, expression: Expression, ignore=set()):
        if expression is Token.LeftBracket:
            return self.parse_expression(self.parse_array(expression), ignore)
        elif type(expression) is Token:
            if expression is Token.LeftParenthesis:
                token = self.source.look()
                inner_expression = self.parse_expression(token, ignore | {Token.RightParenthesis})
                token = self.source.look()

                if token is not Token.RightParenthesis:
                    raise SyntaxError(f"unclosed parenthesized expression. at line {expression.line} in '{self.filename}'")
                
                return self.parse_expression(Parenthesized(inner_expression), ignore)

            raise SyntaxError(f"unexpected token {expression}. at line {expression.line} in '{self.filename}'")
        
        token = self.source.look()

        BINARYOPERATION_TOKENS = {Token.Plus, Token.Minus, Token.Star, Token.Slash, Token.Percent, Token.Ampersand, Token.VerticalBar, Token.Caret, Token.LessThan, Token.GreaterThan, Token.NotEqual, Token.EqualEqual, Token.LessThanEqual, Token.GreaterThanEqual}

        if type(token) is not Token:
            pass
        elif token in ignore:
            pass
        elif token in BINARYOPERATION_TOKENS:
            return BinaryOperation(expression, token, self.parse_expression(self.source.look(), ignore))
        elif token is Token.Dot:
            return self.parse_expression(Dot(expression, self.parse_expression(self.source.look(), ignore | {Token.LeftParenthesis} | BINARYOPERATION_TOKENS)), ignore)
        elif token is Token.LeftParenthesis and (type(expression) is Name or type(expression) is Dot):
            return self.parse_expression(self.parse_call(expression), ignore)
        elif token is Token.LeftBrace:
            return self.parse_expression(self.parse_struct(expression), ignore)
        elif type(expression) is Name and token is Token.LeftBracket:
            return self.parse_expression(Item(expression, self.parse_array(token)), ignore)

        self.source.unlook()

        return expression
    
    def parse_import(self):
        expression = self.parse_expression(self.source.look())

        if type(expression) is not Dot and type(expression) is not Name:
            raise SyntaxError(f"import expects a module name, found {expression}. at line {expression.line} in '{self.filename}'")

        return Import(expression)
    
    def parse_return(self):
        return Return(self.parse_expression(self.source.look()))
    
    def parse_enum_declaration(self):
        name = self.source.look()

        if type(name) is not Name:
            raise SyntaxError(f"enum expects a name, found {name}. at line {name.line} in '{self.filename}'")
        
        if (token := self.source.look()) is not Token.LeftBrace:
            raise SyntaxError(f"enum expects '{{', found {token}. at line {token.line} in '{self.filename}'")
        
        members = []

        for token in self.source:
            if token is Token.EndOfFile:
                raise SyntaxError(f"unclosed enum body '{name}'. at line {name.line} in '{self.filename}'")
            elif token is Token.RightBrace:
                break

            argument = self.parse_expression(token, {Token.Comma, Token.RightBrace})
            
            if argument:
                members.append(argument)

        return EnumDeclaration(name, members)
    
    def parse_struct_declaration(self):
        name = self.parse_expression(self.source.look(), {Token.LeftBrace})

        if type(name) is not Item and type(name) is not Name:
            raise SyntaxError(f"struct expects a name, found {name}. at line {name.line} in '{self.filename}'")
        
        if (token := self.source.look()) is not Token.LeftBrace:
            raise SyntaxError(f"enum expects '{{', found {token}. at line {token.line} in '{self.filename}'")

        members = {}
        methods = {}

        for token in self.source:
            if token is Token.EndOfFile:
                raise SyntaxError(f"unclosed enum body '{name}'. at line {name.line} in '{self.filename}'")
            elif token is Token.RightBrace:
                break

            if token is Keyword.Fun:
                function = self.parse_function_declaration()
                signatures = methods.setdefault(function.name, {})
                signatures[function.head.signature] = function
                continue

            member_name = token

            if type(member_name) is not Name:
                raise SyntaxError(f"struct {name} expects a member name, found {member_name}. at line {member_name.line} in '{self.filename}'")
            
            if (token := self.source.look()) is not Token.Colon:
                raise SyntaxError(f"struct {name} expects a ':' after member name {member_name}, found {token}. at line {member_name.line} in '{self.filename}'")
        
            member_kind = self.parse_expression(self.source.look(), {Token.Comma, Token.RightBrace})
            
            if type(member_kind) is not Dot and type(member_kind) is not Name:
                raise SyntaxError(f"struct member {member_name} must have a valid type, found {member_kind}. at {member_kind.line} in '{self.filename}'")
            
            members[member_name] = Type(member_kind)

        return StructDeclaration(name, members, methods)
    
    def parse_struct(self, name: Name):
        values = []

        for token in self.source:
            if token is Token.EndOfFile:
                raise SyntaxError(f"unclosed enum body '{name}'. at line {name.line} in '{self.filename}'")
            elif token is Token.RightBrace:
                break

            value = self.parse_expression(token, {Token.Comma, Token.RightBrace})
            
            if value:
                values.append(value)

            token = self.source.look()

            if token is Token.Comma:
                continue
            elif token is Token.RightBrace:
                break
            elif token is Token.EndOfFile:
                raise SyntaxError(f"unclosed struct literal '{name}'. at line {name.line} in '{self.filename}'")
            else:
                raise SyntaxError(f"expecting ',' or '}}' after struct literal argument {value}. at line {value.line} in '{self.filename}'")
        
        return Struct(name, values)
    
    def parse_body(self):
        if (token := self.source.look()) is not Token.LeftBrace:
            raise SyntaxError(f"bodies must starts with '{{', found {token}. at line {token.line} in '{self.filename}'")
        
        left_brace = token
        lines = []

        for token in self.source:
            if token is Token.EndOfFile:
                raise SyntaxError(f"unclosed body. at line {left_brace.line} in '{self.filename}'")
            elif token is Token.RightBrace:
                break

            if token is Keyword.Import:
                lines.append(self.parse_import())
            elif token is Keyword.Enum:
                lines.append(self.parse_enum_declaration())
            elif token is Keyword.Struct:
                lines.append(self.parse_struct_declaration())
            elif token is Keyword.Fun:
                lines.append(self.parse_function_declaration())
            elif token is Keyword.Let:
                lines.append(self.parse_let())
            elif token is Keyword.While:
                lines.append(self.parse_while())
            elif token is Keyword.If:
                lines.append(self.parse_if())
            elif token is Keyword.Else:
                lines.append(self.parse_else())
            elif token is Keyword.Return:
                lines.append(self.parse_return())
            else:
                parsed_expression = self.parse_expression(token, {Token.Equal, Token.PlusEqual, Token.MinusEqual, Token.StarEqual, Token.SlashEqual, Token.PercentEqual, Token.AmpersandEqual, Token.CaretEqual, Token.VerticalBarEqual})
                token = self.source.look()

                if token in {Token.Equal, Token.PlusEqual, Token.MinusEqual, Token.StarEqual, Token.SlashEqual, Token.PercentEqual, Token.AmpersandEqual, Token.CaretEqual, Token.VerticalBarEqual}:
                    lines.append(self.parse_assignment(parsed_expression, token))
                else:
                    self.source.unlook()
                    lines.append(parsed_expression)
        
        return Body(lines)

    def parse_function_head(self):
        name = self.source.look()

        if type(name) is not Name:
            raise SyntaxError(f"fun expects a name, found {name}. at line {name.line} in '{self.filename}'")
        
        if (token := self.source.look()) is not Token.LeftParenthesis:
            raise SyntaxError(f"function head {name} expects '(', found {token}. at line {token.line} in '{self.filename}'")

        parameters = {}

        for token in self.source:
            if token is Token.RightParenthesis:
                break

            parameter_name = token

            if type(parameter_name) is not Name:
                raise SyntaxError(f"fun {name} expects a parameter name, found {parameter_name}. at line {parameter_name.line} in '{self.filename}'")
            
            if (token := self.source.look()) is not Token.Colon:
                raise SyntaxError(f"fun {name} expects a ':' after parameter name {parameter_name}, found {token}. at line {parameter_name.line} in '{self.filename}'")
            
            parameter_kind = self.parse_expression(self.source.look(), {Token.Comma, Token.RightBrace})
            
            if type(parameter_kind) is not Dot and type(parameter_kind) is not Item and type(parameter_kind) is not Name:
                raise SyntaxError(f"struct member {parameter_kind} must have a valid type, found {parameter_kind}. at {parameter_kind.line} in '{self.filename}'")
            
            parameters[parameter_name] = Type(parameter_kind)

            token = self.source.look()

            if token is Token.Comma:
                continue
            elif token is Token.RightParenthesis:
                break
            elif token is Token.EndOfFile:
                raise SyntaxError(f"unclosed function declaration head '{name}'. at line {name.line} in '{self.filename}'")
            else:
                raise SyntaxError(f"expecting ',' or ')' after function declaration parameter. at line {token.line} in '{self.filename}'")
        
        kind = self.parse_expression(self.source.look(), {Token.LeftBrace})

        if type(kind) is not Dot and type(kind) is not Name:
            raise SyntaxError(f"invalid function return type, found {kind}. at {name.line} in '{self.filename}'")

        return FunctionHead(name, Type(kind), parameters)

    def parse_function_declaration(self):
        return FunctionDeclaration(self.parse_function_head(), self.parse_body())
    
    def parse_extern(self):
        token = self.source.look()

        if token is not Keyword.Fun:
            raise NotImplementedError(f"extern without fun is not implemented. in '{self.filename}'")

        return Extern(self.parse_function_head())

    def parse_let(self):
        name = self.source.look()

        if type(name) is not Name:
            raise SyntaxError(f"let expects a variable name, found '{name.format}'. at line {name.line} in '{self.filename}'")

        if (token := self.source.look()) is not Token.Colon:
            raise SyntaxError(f"let '{name.format}' expects a ':' after variable name, found {token}. at line {name.line} in '{self.filename}'")
        
        kind = self.parse_expression(self.source.look())
        
        if type(kind) is not Dot and type(kind) is not Item and type(kind) is not Name:
            raise SyntaxError(f"let {name} expects a variable type. found {kind}. at line {name.line} in '{self.filename}'")
        
        if (token := self.source.look()) is not Token.Equal:
            raise SyntaxError(f"let {name} expects a '=' after head, found {token}. at line {name.line} in '{self.filename}'")
        
        return Let(name, Type(kind), self.parse_expression(self.source.look()))
    
    def parse_assignment(self, head: Expression, operator: Token):
        if type(head) is not Dot and type(head) is not Item and type(head) is not Name:
            raise SyntaxError(f"assignment expects a name or item found {head}. at line {head.line} in '{self.filename}'")
        
        return Assignment(head, self.parse_expression(self.source.look()), operator)
    
    def parse_while(self):
        return While(self.parse_expression(self.source.look(), {Token.LeftBrace}), self.parse_body())

    def parse_if(self):
        return If(self.parse_expression(self.source.look(), {Token.LeftBrace}), self.parse_body())
    
    def parse_else(self):
        return Else(self.parse_body())

    def parse(self):
        for token in self.source:
            if token is Token.EndOfFile:
                break

            if token is Keyword.Import:
                yield self.parse_import()
            elif token is Keyword.Enum:
                yield self.parse_enum_declaration()
            elif token is Keyword.Struct:
                yield self.parse_struct_declaration()
            elif token is Keyword.Extern:
                yield self.parse_extern()
            elif token is Keyword.Fun:
                yield self.parse_function_declaration()
            elif token is Keyword.Let:
                yield self.parse_let()
            elif token is Keyword.While:
                yield self.parse_while()
            elif token is Keyword.If:
                yield self.parse_if()
            elif token is Keyword.Else:
                yield self.parse_else()
            elif token is Keyword.Return:
                yield self.parse_return()
            elif type(token) is Name:
                head = self.parse_expression(token)
                next_token = self.source.look()

                if next_token is Token.Equal:
                    yield self.parse_assignment(head, next_token)
                else:
                    self.source.unlook()
                    yield head
            else:
                yield self.parse_expression(token)
        
        return