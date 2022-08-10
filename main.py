from argparse import ArgumentParser
from dataclasses import replace
from os import path

from greek.control import Control
from greek import lexer
from greek import parser
from greek import linter
from greek import compiler


def compile(file: str, output: str=None):
    tokens = list(lexer.lex(Control(open(file).read())))
    asts = list(parser.parse(Control(tokens)))
    scope = linter.lint(asts)

    if output is None:
        for compiled in compiler.compile(scope):
            print(compiled)
    
    else:
        stream = open(output, 'w')

        for compiled in compiler.compile(scope):
            stream.write(compiled)
            stream.write('\n')
    
    return

argparser = ArgumentParser()
argparser.add_argument('file')
argparser.add_argument('-o', '--output')

def main():
    arguments = argparser.parse_args()

    if arguments.file is None:
        return argparser.print_usage()

    return compile(arguments.file, arguments.output)

if __name__ == '__main__':
    main()