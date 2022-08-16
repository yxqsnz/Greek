from enum import Enum
from dataclasses import dataclass

from .control import Control

class BaseToken:
    value: str
    line: int=0

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
    Line=               '\n'
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
    At=                 '@'
    Ampersand=          '&'
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
    From=               'from'
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
    def __init__(self, value: str, line=-1):
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Name({self.value})'

class Literal(BaseToken):
    def __init__(self, value: str | int | float | bool, line=-1):
        self.value = value
        self.line = line
    
    def __repr__(self):
        return f'Literal({self.value})'

    def __bool__(self):
        return True

class Comment(BaseToken):
    def __init__(self, value: str | int | float | bool, line=-1):
        self.value = value
        self.line = line
        
    def __repr__(self):
        return f'Comment({self.value})'

@dataclass
class Lexing:
    line: int=1

def lex_scan_name(lexing: Lexing, seeker: Control, value: str) -> Name:
    for char in seeker:
        if char >= 'a' and char <= 'z':
            value += char
        elif char == '_' or char >= 'A' and char <= 'Z' or char >= '0' and char <= '9':
            value += char
        else:
            break
    
    seeker.drop()
    
    return Name(value, line=lexing.line)

def lex_scan_token(lexing: Lexing, seeker: Control) -> Token:
    seeker.drop()

    for token in TOKENS:
        if seeker.equals(token):
            return token
    
    raise SyntaxError(f"invalid token '{seeker.take()}'. at line {lexing.line}")

def lex_scan_stringliteral(lexing: Lexing, seeker: Control, quote: str) -> Literal:
    value = ''

    for char in seeker:
        if char != quote:
            value += char
        else:
            break

    return Literal(value, line=lexing.line)

def lex_scan_comment(lexing: Lexing, seeker: Control) -> Comment:
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

    return Comment(value, line=lexing.line)

def lex_scan_numericliteral(lexing: Lexing, seeker: Control, value: str) -> Literal:
    char = ''

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
        
        if char:
            seeker.drop()
        
        return Literal(float(value), line=lexing.line)
    
    if char:
        seeker.drop()

    return Literal(int(value), line=lexing.line)

def lex(seeker: Control):
    lexing = Lexing()

    for char in seeker:
        if char == '':
            break

        if char == ' ' or char == '\t':
            continue
        elif char == '\n':
            lexing.line += 1
            yield Token.Line
            continue
        

        if char == '#':
            yield lex_scan_comment(lexing, seeker)

        elif char >= 'a' and char <= 'z':
            name = lex_scan_name(lexing, seeker, char)

            if name.value in KEYWORDS:
                yield Keyword(name.value)
            else:
                yield name
        
        elif char == '_' or char >= 'A' and char <= 'Z':
            yield lex_scan_name(lexing, seeker, char)
        elif char >= '0' and char <= '9':
            yield lex_scan_numericliteral(lexing, seeker, char)
        elif char == '"' or char == "'":
            yield lex_scan_stringliteral(lexing, seeker, char)
        else:
            yield lex_scan_token(lexing, seeker)
    
    yield Token.EndOfFile
