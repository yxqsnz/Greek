from argparse import ArgumentParser
from os import path

from greek.compiler import Compiler, Compilation
from greek.source import Source
from greek.lexer import Lexer
from greek.parser import Parser
from greek.checker import Module, Checker


def compile(file: str, output: str=None):
    tokens = tuple(Lexer(Source(open(file).read())))
    asts = tuple(Parser(Source(tokens)))
    checker = Checker(asts, Module.new("main"))

    lines = [
        '#define _CRT_SECURE_NO_WARNINGS',
        '#define _CRT_NONSTDC_NO_DEPRECATE',

        '#define any char*',
        '#define str char*',
        '#define ptr char*',

        '#include <stdbool.h>',
        '#include <stdio.h>',
        '#include <stdlib.h>',
        '#include <string.h>',
        '#include <memory.h>',
        '#include <malloc.h>',
    ]

    for code in Compiler(checker.check(), Compilation.new()):
        lines.append(code)
    
    if output is None:
        for line in lines:
            print(line)
    else:
        open(output, 'w').write("\n".join(lines))
    
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