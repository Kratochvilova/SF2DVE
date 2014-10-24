# -*- coding: utf-8 -*-
"""
Created on Sat Oct 18 16:48:32 2014

@author: pavla
"""

from ply import lex, yacc

class notSupportedException(Exception): pass

tokens = ("OPEN_BRACKET", "CLOSE_BRACKET", "OPEN_BRACE", "CLOSE_BRACE", 
          "SLASH", "WHITESPACE", "ACTION_PART")

t_OPEN_BRACKET = r"\["
t_CLOSE_BRACKET = r"\]"
t_OPEN_BRACE = r"\{"
t_CLOSE_BRACE = r"\}"
t_SLASH = r"/"
t_WHITESPACE = r"\s+"
t_ACTION_PART = r"[^\[\]{}/\s]+"

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
          | EMPTY"""

def p_actions(p):
    "A : ACTION_PART A2"
    if (p[2] == None):
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_whitespace(p):
    "A : WHITESPACE A2"
    if (p[2] == None):
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_slash(p):
    "A : SLASH A2"
    if (p[2] == None):
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_brackets(p):
    """A : OPEN_BRACKET A2 CLOSE_BRACKET A2
         | OPEN_BRACE A2 CLOSE_BRACE A2"""
    if p[2] == None:
        if p[4] == None:
            p[0] = p[1] + p[3]
        else:
            p[0] = p[1] + p[3] + p[4]
    else:
        if p[4] == None:
            p[0] = p[1] + p[2] + p[3]
        else:
            p[0] = p[1] + p[2] + p[3] + p[4]

def p_action(p):
    """A2 : A
          | EMPTY"""
    p[0] = p[1]
    
def p_incorrect_c_action(p):
    "INCORRECT_C_ACTION : ACTION_PART A2"
    raise notSupportedException("Condition actions must be enclosed in curly "
                                "brackets.")

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line {0}: {1}".format(p.lineno + 1, p.type))

lexer = lex.lex()
parser = yacc.yacc()

def parse(text, lexer=lexer):
    return parser.parse(text, lexer)
