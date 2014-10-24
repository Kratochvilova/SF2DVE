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

tokens = (["AL_NUM", "NON_AL_NUM", "COLON"] + list(keywords.values()))

def t_AL_NUM(t):
    r"\w+"
    t.type = keywords.get(t.value, "AL_NUM")
    return t

t_NON_AL_NUM = r"[^:\w]+"
t_COLON = r":"

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_label(p):
    """LABEL : KEYWORDS ACTIONS LABEL
             | EMPTY"""
    if len(p) == 4:
        if p[3] == None:
            p[0] = [[p[1], p[2]]]
        else:
            p[0] = [[p[1], p[2]]] + p[3]
    else:
        p[0] = p[1]

def p_empty(p):
    "EMPTY :"
    pass

def p_keywords(p):
    """KEYWORDS : KEYWORD NON_AL_NUM KEYWORDS
                | KEYWORD COLON"""
    if len(p) == 4:
        p[0] = [p[1]] + p[3]
    else:
        p[0] = [p[1]]

def p_keyword(p):
    """KEYWORD : EN
               | DU
               | EX
               | ENTRY
               | DURING
               | EXIT"""
    p[0] = p[1]

def p_actions(p):
    """ACTIONS : AL_NUM ACTIONS
               | NON_AL_NUM ACTIONS
               | COLON ACTIONS
               | AL_NUM
               | NON_AL_NUM
               | COLON"""
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1]

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line {0}: {1}".format(p.lineno, p.type))

lexer = lex.lex()
parser = yacc.yacc()

def parse(text, lexer=lexer):
    return parser.parse(text, lexer)
    