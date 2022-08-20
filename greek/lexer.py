from dataclasses import dataclass
from enum import Enum

from .source import Source

class BaseToken:
    value: str
    line: int=0

    def __bool__(self):
        return True

    def __len__(self):
        return len(self.value)
    
    def __hash__(self):
        return hash(self.value)
    
    def __eq__(self, value: str):
        return self.value == value
    
    @property
    def kind(self):
        return Name(type(self).__name__)
        
    @property
    def format(self):
        return str(self.value)

class Token(BaseToken, Enum):
    EndOfFile=          '\0'
    LeftParenthesis=    '('
    RightParenthesis=   ')'
    LeftBrace=          '{'
    RightBrace=         '}'
    LeftBracket=        '['
    RightBracket=       ']'
    Not=                '!'
    Equal=              '='
    LessThan=           '<'
    GreaterThan=        '>'
    Plus=               '+'
    Minus=              '-'
    Star=               '*'
    Slash=              '/'
    Percent=            '%'
    Ampersand=          '&'
    VerticalBar=        '|'
    Caret=              '^'
    Tilde=              '~'
    NotEqual=           '!='
    EqualEqual=         '=='
    LessThanEqual=      '<='
    GreaterThanEqual=   '>='
    PlusEqual=          '+='
    MinusEqual=         '-='
    StarEqual=          '*='
    SlashEqual=         '/='
    PercentEqual=       '%='
    AmpersandEqual=     '&='
    VerticalBarEqual=   '|='
    CaretEqual=         '^='
    Colon=              ':'
    Semicolon=          ';'
    Dot=                '.'
    Comma=              ','

class Keyword(BaseToken, Enum):
    Extern=             'extern'
    Import=             'import'
    Struct=             'struct'
    Enum=               'enum'
    Let=                'let'
    Fun=                'fun'
    Return=             'return'
    If=                 'if'
    Else=               'else'
    While=              'while'
    For=                'for'
    In=                 'in'

TOKENS = sorted(Token.__members__.values(), key=len, reverse=True)
KEYWORDS = sorted(Keyword.__members__.values(), key=len, reverse=True)

@dataclass(eq=False)
class Name(BaseToken):
    value: str
    line: int=0

    def __hash__(self):
        return hash(self.value)

@dataclass(eq=False)
class Type(BaseToken):
    value: Name

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, value: str):
        if self.value == Name('any'):
            return True
        elif self.value == Name('ptr'):
            return True

        return self.value == value
    
    @property
    def format(self):
        return self.value.format
    
    @property
    def kind(self):
        return type(self)(Name('type'))

class Literal(Name):
    value: str | int | float

    @property
    def kind(self):
        if type(self.value) is str:
            return Type(Name('str'))
        elif type(self.value) is int:
            return Type(Name('int'))
        elif type(self.value) is float:
            return Type(Name('float'))
        elif type(self.value) is bool:
            return Type(Name('float'))
        
        return Type(Name('void'))

    @property
    def format(self):
        return repr(self.value)

class Comment(Name):
    value: str

class Lexer:
    def __init__(self, source: Source, position=0, line=1):
        self.source = source
        self.position = position
        self.line = line
    
    def __iter__(self):
        return self.lex()
    
    def scan_token(self) -> Token:
        self.source.unlook()

        for token in TOKENS:
            token_length = len(token)

            if self.source.look(token_length) == token:
                token.line = self.line

                return token
            
            self.source.unlook(token_length)

        raise SyntaxError(f"unknown token {self.source.look()!r} at line {self.line}")
    
    def scan_name_keyword_or_bool_literal(self, value: str) -> Name | Keyword | Literal:
        char = ''

        for char in self.source:
            if char >= 'a' and char <= 'z' or char >= 'A' and char <= 'Z' or char == '_':
                value += char
            else:
                self.source.unlook()
                break
        
        if value in KEYWORDS:
            keyword = Keyword(value)
            keyword.line = self.line

            return keyword
        elif value == "true":
            return Literal(True)
        elif value == "false":
            return Literal(False)

        return Name(value, self.line)
    
    def scan_string_literal(self, quote: str):
        value = ''

        for char in self.source:
            if char != quote:
                value += char
            else:
                break
        
        return Literal(value, self.line)
    
    def scan_numeric_literal(self, value: str):
        char = ''

        for char in self.source:
            if char >= '0' and char <= '9' or char == '_':
                value += char
            else:
                if char == '.':
                    value += char

                    for char in self.source:
                        if char >= '0' and char <= '9' or char == '_':
                            value += char
                        else:
                            self.source.unlook()
                            break
                    
                    return Literal(float(value), self.line) 
                
                self.source.unlook()
                break

        return Literal(int(value), self.line)
    
    def scan_comment(self, value: str):
        for char in self.source:
            if char != '\n':
                value += char
            else:
                break
        
        comment = Comment(value.strip(), self.line)
        self.line += 1

        return comment

    def lex(self):
        for char in self.source:
            if char == ' ' or char == '\t':
                continue
            elif char == '\n':
                self.line += 1
                continue

            if char >= 'a' and char <= 'z' or char >= 'A' and char <= 'Z' or char == '_':
                yield self.scan_name_keyword_or_bool_literal(char)
            elif char >= '0' and char <= '9':
                yield self.scan_numeric_literal(char)
            elif char == '"' or char == "'":
                yield self.scan_string_literal(char)
            elif char == '#':
                yield self.scan_comment(char)
            else:
                yield self.scan_token()
        
        token = Token.EndOfFile
        token.line = self.line

        yield token