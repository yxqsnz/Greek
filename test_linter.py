from greek.control import Control
from greek import lexer
from greek import parser
from greek import linter

from pprint import pprint

tokens = list(lexer.lex(Control(open('examples/hello_world.greek').read())))
asts = list(parser.parse(Control(tokens)))
scope = linter.lint(asts)

print(pprint(scope))
