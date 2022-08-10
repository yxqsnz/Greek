from greek.control import Control
from greek import lexer
from greek import parser

tokens = list(lexer.lex(Control(open('examples/hello_world.greek').read())))

for ast in parser.parse(Control(tokens)):
    print(repr(ast))
