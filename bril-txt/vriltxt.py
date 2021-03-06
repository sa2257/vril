"""A text format for Bril.

This module defines both a parser and a pretty-printer for a
human-editable representation of Bril programs. There are two commands:
`vril2txt`, which takes a Bril program in its (canonical) JSON format and
pretty-prints it in the text format, and `vril2json`, which parses the
format and emits the ordinary JSON representation.
"""

import lark
import sys
import json

__version__ = '0.0.1'


# Text format parser.

# in case we need to add an array lit it's - array: "[" [SIGNED_INT ("," SIGNED_INT)*] "] from https://github.com/lark-parser/lark/blob/master/docs/json_tutorial.md#conclusion"

# CNAME is CNAME: ("_"|LETTER) ("_"|LETTER|DIGIT)* from https://github.com/lark-parser/lark/blob/master/lark/grammars/common.lark

# Currently this spec should allow
# name: array = init number;
# name[number]: int = v2a name;
# name: int = a2v name[number]

# To start with AELEM and array names are separate
# Also AELEM can have arbitrary sequences of [ and ] not one and only [INT]

#a2v.7: IDENT ":" type "=" "a2v" AELEM ";"
# The order might matter! aop sent down to 3
# If we want to constraint how arrays are written
# AELEM: IDENT "[" INT "]"

GRAMMAR = """
start: func*

func: CNAME "{" instr* "}"

?instr: const | vop | eop | label | init | aop

init.6: IDENT ":" type "=" "init" lit ";"
const.5: IDENT ":" type "=" "const" lit ";"
vop.4: IDENT ":" type "=" CNAME IDENT* ";"
aop.3: AIDENT ":" type "=" CNAME AIDENT* ";"
eop.2: CNAME IDENT* ";"
label.1: IDENT ":"

lit: SIGNED_INT  -> int
  | BOOL     -> bool

type: CNAME
BOOL: "true" | "false"
IDENT: ("_"|"%"|LETTER) ("_"|"%"|"."|LETTER|DIGIT)*
COMMENT: /#.*/
AIDENT: ("_"|"%"|LETTER) ("_"|"%"|"."|LETTER|DIGIT|"["|"]")*

%import common.SIGNED_INT
%import common.WS
%import common.CNAME
%import common.LETTER
%import common.DIGIT
%ignore WS
%ignore COMMENT
""".strip()


class JSONTransformer(lark.Transformer):
    def start(self, items):
        return {'functions': items}

    def func(self, items):
        name = items.pop(0)
        return {'name': str(name), 'instrs': items}

    def init(self, items):
        dest = items.pop(0)
        type = items.pop(0)
        val = items.pop(0)
        return {
            'op': 'init',
            'dest': str(dest),
            'type': type,
            'value': val,
        }

    def const(self, items):
        dest = items.pop(0)
        type = items.pop(0)
        val = items.pop(0)
        return {
            'op': 'const',
            'dest': str(dest),
            'type': type,
            'value': val,
        }

    def aop(self, items):
        dest = items.pop(0)
        type = items.pop(0)
        op = items.pop(0)
        return {
            'op': str(op),
            'dest': str(dest),
            'type': type,
            'args': [str(t) for t in items],
         }

    def vop(self, items):
        dest = items.pop(0)
        type = items.pop(0)
        op = items.pop(0)
        return {
            'op': str(op),
            'dest': str(dest),
            'type': type,
            'args': [str(t) for t in items],
         }

    def eop(self, items):
        op = items.pop(0)
        return {
            'op': str(op),
            'args': [str(t) for t in items],
         }

    def label(self, items):
        name = items.pop(0)
        return {
            'label': name,
        }

    def int(self, items):
        return int(str(items[0]))

    def bool(self, items):
        if str(items[0]) == 'true':
            return True
        else:
            return False

    def type(self, items):
        return str(items[0])


def parse_bril(txt):
    parser = lark.Lark(GRAMMAR)
    tree = parser.parse(txt)
    data = JSONTransformer().transform(tree)
    return json.dumps(data, indent=2, sort_keys=True)


# Text format pretty-printer.

def instr_to_string(instr):
    if instr['op'] == 'const':
        return '{}: {} = const {}'.format(
            instr['dest'],
            instr['type'],
            str(instr['value']).lower(),
        )
    elif instr['op'] == 'init':
        return '{}: {} = init {}'.format(
            instr['dest'],
            instr['type'],
            str(instr['value']).lower(),
        )
    elif 'dest' in instr:
        return '{}: {} = {} {}'.format(
            instr['dest'],
            instr['type'],
            instr['op'],
            ' '.join(instr['args']),
        )
    else:
        return '{} {}'.format(
            instr['op'],
            ' '.join(instr['args']),
        )


def print_instr(instr):
    print('  {};'.format(instr_to_string(instr)))


def print_label(label):
    print('{}:'.format(label['label']))


def print_func(func):
    print('{} {{'.format(func['name']))
    for instr_or_label in func['instrs']:
        if 'label' in instr_or_label:
            print_label(instr_or_label)
        else:
            print_instr(instr_or_label)
    print('}')


def print_prog(prog):
    for func in prog['functions']:
        print_func(func)


# Command-line entry points.

def vril2json():
    print(parse_bril(sys.stdin.read()))


def vril2txt():
    print_prog(json.load(sys.stdin))
