from greek.source import Source
from greek.lexer import Lexer
from greek.parser import Parser

from greek.checker import Module
from greek.checker import Checker

tokens = tuple(Lexer(Source(open("examples/hello_world.greek").read())))
asts = tuple(Parser(Source(tokens)))

checker = Checker(asts, Module.new("main"))
checker.check()