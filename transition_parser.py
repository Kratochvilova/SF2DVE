#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 18 16:48:32 2014

@author: pavla
"""

from ply import lex, yacc
from extendedExceptions import notSupportedException

tokens = ("OPEN_BRACKET", "CLOSE_BRACKET", "OPEN_BRACE", "CLOSE_BRACE", 
          "SLASH", "WHITESPACE", "NEWLINE", "OTHER")

t_OPEN_BRACKET = r"\["
t_CLOSE_BRACKET = r"\]"
t_OPEN_BRACE = r"\{"
t_CLOSE_BRACE = r"\}"
t_SLASH = r"/"
t_WHITESPACE = r"[ \t\r\f\v]+"
t_OTHER = r"[^\[\]{}/\s]+"

def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    return t

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_label(p):
    """LABEL : WS CONDITION C_ACTION T_ACTION
             | WS CONDITION INCORRECT_C_ACTION"""
    p[0] = [p[2], p[3], p[4]]

def p_condition(p):
    """CONDITION : OPEN_BRACKET A CLOSE_BRACKET WS
                 | EMPTY"""
    if (len(p) == 5):
        p[0] = p[2]
    else:
        p[0] = p[1]

def p_c_action(p):
    """C_ACTION : OPEN_BRACE A CLOSE_BRACE WS
                | EMPTY"""
    if (len(p) == 5):
        p[0] = p[2]
    else:
        p[0] = p[1]

def p_t_action(p):
    """T_ACTION : SLASH A
                | EMPTY"""
    if (len(p) == 3):
        p[0] = p[2]
    else:
        p[0] = p[1]

def p_empty(p):
    "EMPTY :"
    pass

def p_ws(p):
    """WS : WHITESPACE
          | NEWLINE
          | EMPTY"""

def p_action_parts(p):
    """A : OTHER A2
         | WHITESPACE A2
         | NEWLINE A2
         | SLASH A2"""
    if (p[2] is None):
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_brackets(p):
    """A : OPEN_BRACKET A2 CLOSE_BRACKET A2
         | OPEN_BRACE A2 CLOSE_BRACE A2"""
    if p[2] is None:
        if p[4] is None:
            p[0] = p[1] + p[3]
        else:
            p[0] = p[1] + p[3] + p[4]
    else:
        if p[4] is None:
            p[0] = p[1] + p[2] + p[3]
        else:
            p[0] = p[1] + p[2] + p[3] + p[4]

def p_action(p):
    """A2 : A
          | EMPTY"""
    p[0] = p[1]
    
def p_incorrect_c_action(p):
    "INCORRECT_C_ACTION : OTHER A2"
    raise notSupportedException("Condition actions must be enclosed in curly "
                                "brackets.")

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line %s: %s" % (p.lineno, p.type))

lexer = lex.lex()
parser = yacc.yacc()

def parse(text, lexer=lexer):
    return parser.parse(text, lexer)
