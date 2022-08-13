from enum import Enum
from dataclasses import dataclass

from .control import Control

class BaseToken:
    value: str

    def __bool__(self):
        return bool(self.value)

    def __len__(self):
        return len(self.value)
    
    def __hash__(self):
        return hash(self.value)
    
    def __eq__(self, value: str):
        return self.value == value

class Token(BaseToken, Enum):
    EndOfFile=          '\x00'
    LeftParenthesis=    '('
    RightParenthesis=   ')'
    LeftBrace=          '{'
    RightBrace=         '}'
    LeftBracket=        '['
    RightBracket=       ']'
    Equal=              '='
    LessThan=           '<'
    GreaterThan=        '>'
    Plus=               '+'
    Minus=              '-'
    Star=               '*'
    Slash=              '/'
    Percent=            '%'
    At=                 '@'
    NotEqual=           '!='
    EqualEqual=         '=='
    LessThanEqual=      '<='
    GreaterThanEqual=   '>='
    PlusEqual=          '+='
    MinusEqual=         '-='
    StarEqual=          '*='
    SlashEqual=         '/='
    PercentEqual=       '%='
    Colon=              ':'
    Semicolon=          ';'
    Dot=                '.'
    Comma=              ','
    ColonColon=         '::'

TOKENS = sorted(Token.__members__.values(), key=len, reverse=True)

class Keyword(BaseToken, Enum):
    Import=             'import'
    Extern=             'extern'
    Struct=             'struct'
    Enum=               'enum'
    Fun=                'fun'
    Return=             'return'
    Let=                'let'
    If=                 'if'
    Else=               'else'
    While=              'while'
    For=                'for'
    In=                 'in'

KEYWORDS = sorted(Keyword.__members__.values(), key=len, reverse=True)

class Name(BaseToken):
    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return f'Name({self.value})'

class Literal(BaseToken):
    def __init__(self, value: str | int | float | bool):
        self.value = value
        
    def __repr__(self):
        return f'Literal({self.value})'

class Comment(BaseToken):
    def __init__(self, value: str | int | float | bool):
        self.value = value
        
    def __repr__(self):
        return f'Comment({self.value})'

def lex_scan_name(seeker: Control, value: str) -> Name:
    for char in seeker:
        if char >= 'a' and char <= 'z':
            value += char
        elif char == '_' or char >= 'A' and char <= 'Z' or char >= '0' and char <= '9':
            value += char
        else:
            break
    
    seeker.drop()
    
    return Name(value)

def lex_scan_token(seeker: Control) -> Token:
    seeker.drop()

    for token in TOKENS:
        if seeker.equals(token):
            return token
    
    raise SyntaxError(f"invalid token '{seeker.take()}'. at position {seeker.position}")

def lex_scan_stringliteral(seeker: Control, quote: str) -> Literal:
    value = ''

    for char in seeker:
        if char != quote:
            value += char
        else:
            break

    return Literal(value)

def lex_scan_comment(seeker: Control) -> Comment:
    value = ''

    while seeker.take() == ' ':
        continue
    else:
        seeker.drop()

    for char in seeker:
        if char != '\n':
            value += char
        else:
            break

    return Comment(value)

def lex_scan_numericliteral(seeker: Control, value: str) -> Literal:
    for char in seeker:
        if char == '_' or char >= '0' and char <= '9':
            value += char
        else:
            break
    
    if char == '.':
        value += '.'

        for char in seeker:
            if char == '_' or char >= '0' and char <= '9':
                value += char
            else:
                break
        
        seeker.drop()
        
        return Literal(float(value))
    
    seeker.drop()

    return Literal(int(value))

def lex(seeker: Control):
    for char in seeker:
        if char == ' ' or char == '\n' or char == '\t':
            continue
        
        if char == '#':
            yield lex_scan_comment(seeker)

        elif char >= 'a' and char <= 'z':
            name = lex_scan_name(seeker, char)

            if name.value in KEYWORDS:
                yield Keyword(name.value)
            else:
                yield name
        
        elif char == '_' or char >= 'A' and char <= 'Z':
            yield lex_scan_name(seeker, char)
        elif char >= '0' and char <= '9':
            yield lex_scan_numericliteral(seeker, char)
        elif char == '"' or char == "'":
            yield lex_scan_stringliteral(seeker, char)
        else:
            yield lex_scan_token(seeker)
    
    yield Token.EndOfFile