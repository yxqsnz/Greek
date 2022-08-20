from sys import argv

from greek.source import Source
from greek.lexer import Lexer
from greek.parser import Parser

path = argv[-1] if argv[1:] else "examples/hello_world.greek"

tokens = tuple(Lexer(Source(open(path).read())))

for ast in Parser(Source(tokens)):
    print(ast)