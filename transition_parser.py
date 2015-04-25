# -*- coding: utf-8 -*-

# This file is part of sf2dve.
#
#    sf2dve is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 2.1 of the License, or
#    (at your option) any later version.
#
#    sf2dve is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with sf2dve.  If not, see <http://www.gnu.org/licenses/>.

"""
Created on Sat Oct 18 16:48:32 2014

@author: pavla
"""

from ply import lex, yacc
from extendedExceptions import notSupportedException
import os.path

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

directory = os.path.join(os.path.dirname(__file__), 
                         "parser_tables", 
                         os.path.basename(__file__).rsplit('.', 1)[0])

lexer = lex.lex(debug=False, optimize=True, outputdir=directory)
parser = yacc.yacc(debug=False, optimize=True, outputdir=directory)

def parse(text, lexer=lexer):
    return parser.parse(text, lexer)
