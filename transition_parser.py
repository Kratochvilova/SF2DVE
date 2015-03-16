#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 18 16:48:32 2014

@author: pavla
"""

from ply import lex, yacc
from extendedExceptions import notSupportedException

tokens = ("OPEN_BRACKET", "CLOSE_BRACKET", "AL_NUM", "WHITESPACE", "NEWLINE", 
          "OTHER")
literals = r"{}/"

t_OPEN_BRACKET = r"\["
t_CLOSE_BRACKET = r"\]"
t_AL_NUM = r"\w+"
t_WHITESPACE = r"[ \t\r\f\v]+"
t_OTHER = r"[^\[\]{}/\s\w]+"

def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    return t

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_label(p):
    """label : ws events condition c_action t_action
             | ws events OPEN_BRACKET A CLOSE_BRACKET ws incorrect_c_action"""
    if (len(p) == 6):
        p[0] = [p[2], p[3], p[4], p[5]]

def p_events(p):
    """events : AL_NUM ws
              | empty"""
    p[0] = p[1]

def p_condition(p):
    """condition : OPEN_BRACKET A CLOSE_BRACKET ws
                 | empty"""
    if (len(p) == 5):
        p[0] = p[2]

def p_c_action(p):
    """c_action : '{' A '}' ws
                | empty"""
    if (len(p) == 5):
        p[0] = p[2]

def p_t_action(p):
    """t_action : '/' A
                | empty"""
    if (len(p) == 3):
        p[0] = p[2]

def p_empty(p):
    "empty :"
    pass

def p_ws(p):
    """ws : WHITESPACE ws
          | NEWLINE ws
          | empty"""
    if p[1] is None:
        p[0] = ""
    else:
        p[0] = p[1] + p[2]

def p_action(p):
    """A : A2
         | empty"""
    if p[1] is None:
        p[0] = ""
    else:
        p[0] = p[1]

def p_action_parts(p):
    """A2 : AL_NUM A
          | OTHER A
          | WHITESPACE A
          | NEWLINE A
          | '/' A"""
    if (p[2] is None):
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_brackets(p):
    """A2 : OPEN_BRACKET A CLOSE_BRACKET A
          | '{' A '}' A"""
    p[0] = p[1] + p[2] + p[3] + p[4]
    
def p_incorrect_c_action(p):
    """incorrect_c_action : AL_NUM A
                          | OTHER A"""
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
