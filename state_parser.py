#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 23 15:51:31 2014

@author: pavla
"""

from ply import lex, yacc

keywords = {
   "en" : "EN",
   "du" : "DU",
   "ex" : "EX",
   "entry" : "ENTRY",
   "during" : "DURING",
   "exit" : "EXIT"
}

tokens = (["WHITESPACE", "NEWLINE", "AL_NUM", "OTHER"] + list(keywords.values()))
literals = ",;:"

t_WHITESPACE = r"[ \t\r\f\v]+"
t_OTHER = r"[^\s,;:\w]+"

def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    return t

def t_AL_NUM(t):
    r"\w+"
    t.type = keywords.get(t.value, "AL_NUM")
    return t

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_start(p):
    "start : ws label"
    p[0] = p[2]

def p_label(p):
    """label : keywords actions label
             | empty"""
    if len(p) == 4:
        if p[3] is None:
            p[0] = [[p[1], p[2]]]
        else:
            p[0] = [[p[1], p[2]]] + p[3]
    else:
        p[0] = []

def p_empty(p):
    "empty :"
    pass

def p_ws(p):
    """ws : WHITESPACE
          | NEWLINE
          | empty"""
    if p[1] is None:
        p[0] = ""
    else:
        p[0] = p[1]

def p_keywords(p):
    """keywords : keyword separator keyword
                | keyword ws ':'"""
    if p[3] != ':':
        p[0] = [p[1]] + p[3]
    else:
        p[0] = [p[1]]

def p_keyword(p):
    """keyword : EN
               | DU
               | EX
               | ENTRY
               | DURING
               | EXIT"""
    p[0] = p[1]

def p_separator(p):
    """separator : ws ',' ws
                 | ws ';' ws"""
    p[0] = p[2]

def p_actions(p):
    """actions : AL_NUM actions
               | WHITESPACE actions
               | NEWLINE actions
               | ',' actions
               | ';' actions
               | ':' actions
               | OTHER actions
               | AL_NUM
               | WHITESPACE
               | NEWLINE
               | ','
               | ';'
               | ':'
               | OTHER"""
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1]

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    print(repr(p))
    raise ValueError("Syntax error, line %s: %s" % (p.lineno, p.type))

lexer = lex.lex()
parser = yacc.yacc()

def parse(text, lexer=lexer):
    return parser.parse(text, lexer)
