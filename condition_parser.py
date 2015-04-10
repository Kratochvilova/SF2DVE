#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  9 09:35:20 2014

@author: pavla
"""

from ply import lex, yacc

tokens = ("RIGHT_OP", "LEFT_OP", "AND_OP", "OR_OP", "LE_OP", "GE_OP", "EQ_OP",
          "NE_OP", "LBRACKET", "RBRACKET", "NUMBER", "IDENTIFIER")

literals = ";,:=()&!~-+*/%<>^|?"

t_ignore = " \t\r\f\v"
t_ignore_COMMENT = r"(//.*)|(/\*(.|\n)*?\*/)"
t_RIGHT_OP = r">>"
t_LEFT_OP = r"<<"
t_AND_OP = r"&&"
t_OR_OP = r"\|\|"
t_LE_OP = r"<="
t_GE_OP = r">="
t_EQ_OP = r"=="
t_NE_OP = r"!="
t_LBRACKET = r"(\[|<:)"
t_RBRACKET = r"(\]|:>)"
t_NUMBER = r"[0-9]+"
t_IDENTIFIER = r"[a-zA-Z_][a-zA-Z_0-9]*"

def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    
def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_start(p):
    """start : empty
             | logical_or_expression"""
    if p[1] is None:
        p[0] = ""
    else:
        p[0] = p[1]

def p_empty(p):
    "empty :"
    pass

def p_logical_or_expression(p):
    """logical_or_expression : logical_and_expression
            | logical_or_expression OR_OP logical_and_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' or ' + p[3]

def p_logical_and_expression(p):
    """logical_and_expression : inclusive_or_expression
            | logical_and_expression AND_OP inclusive_or_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' and ' + p[3]

def p_inclusive_or_expression(p):
    """inclusive_or_expression : exclusive_or_expression
            | inclusive_or_expression '|' exclusive_or_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_exclusive_or_expression(p):
    """exclusive_or_expression : and_expression
                               | exclusive_or_expression '^' and_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_and_expression(p):
    """and_expression : equality_expression
                      | and_expression '&' equality_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_equality_expression(p):
    """equality_expression : relational_expression
                           | equality_expression EQ_OP relational_expression
                           | equality_expression NE_OP relational_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]
 
def p_relational_expression(p):
    """relational_expression : shift_expression
                             | relational_expression '<' shift_expression
                             | relational_expression '>' shift_expression
                             | relational_expression LE_OP shift_expression
                             | relational_expression GE_OP shift_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_shift_expression(p):
    """shift_expression : additive_expression
                        | shift_expression LEFT_OP additive_expression
                        | shift_expression RIGHT_OP additive_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_additive_expression(p):
    """additive_expression : multiplicative_expression
            | additive_expression '+' multiplicative_expression
            | additive_expression '-' multiplicative_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_multiplicative_expression(p):
    """multiplicative_expression : unary_expression
            | multiplicative_expression '*' unary_expression
            | multiplicative_expression '/' unary_expression
            | multiplicative_expression '%' unary_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_unary_expression(p):
    """unary_expression : primary_expression
                        | unary_operator unary_expression
                        | primary_expression LBRACKET NUMBER RBRACKET"""
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3 and p[1] == '+':
        p[0] = p[2]
    elif len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1] + p[2] + p[3] + p[4]

def p_unary_operator(p):
    """unary_operator : '+'
                      | '-'
                      | '~'
                      | '!'"""
    if p[1] == '-' or p[1] == '~':
        p[0] = p[1]
    if p[1] == '!':
        p[0] = ' not '

def p_primary_expression(p):
    """primary_expression : IDENTIFIER
                          | NUMBER
                          | '(' logical_or_expression ')'"""
    if len(p) == 2:
        p[0] = p[1]
    else: 
        p[0] = p[1] + p[2] + p[3]

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line %s: %s" % (p.lineno, p.type))

lexer = lex.lex()
parser = yacc.yacc()

def parse(text, lexer=lexer):
    return (parser.parse(text, lexer))
