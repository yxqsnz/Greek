from greek.source import Source
from greek.lexer import Lexer
from greek.parser import Parser

for lexer in Lexer(Source(open("examples/hello_world.greek").read())):
    print(lexer)