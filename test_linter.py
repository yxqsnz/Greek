from greek.control import Control
from greek import lexer
from greek import parser
from greek import checker

from pprint import pprint

tokens = list(lexer.lex(Control(open('examples/hello_world.greek').read())))
asts = list(parser.parse(Control(tokens)))
scope = checker.check(asts)

print(repr(scope))
