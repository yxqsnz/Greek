from argparse import ArgumentParser
from os import path

from greek import checker
from greek import compiler


def compile(file: str, output: str=None):
    scope = checker.check_module(compiler.Name(path.splitext(file)[0].replace('/', '.')))

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