#!/bin/env python3
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
   "exit" : "EXIT",
   "bind" : "BIND",
   "on" : "ON",
   "after" : "AFTER",
   "at" : "AT",
   "before" : "BEFORE",
   "every" : "EVERY"
}

tokens = (["WHITESPACE", "NEWLINE", "AL_NUM", "OTHER"] + list(keywords.values()))
literals = ",;:()"

t_WHITESPACE = r"[ \t\r\f\v]+"
t_OTHER = r"[^\s,;:()\w]+"

def t_AL_NUM(t):
    r"\w+"
    t.type = keywords.get(t.value, "AL_NUM")
    return t

def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    return t

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_start(p):
    "start : ws label"
    p[0] = p[2]

def p_label(p):
    """label : action_keywords actions label
             | bind actions label
             | on actions label
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
    """ws : WHITESPACE ws
          | NEWLINE ws
          | empty"""
    if p[1] is None:
        p[0] = ""
    else:
        p[0] = p[1] + p[2]

def p_keywords(p):
    """action_keywords : action_keyword separator action_keywords
                       | action_keyword ws ':'"""
    if p[3] != ':':
        p[0] = [p[1]] + p[3]
    else:
        p[0] = [p[1]]

def p_keyword(p):
    """action_keyword : EN
                      | DU
                      | EX
                      | ENTRY
                      | DURING
                      | EXIT"""
    p[0] = p[1]

def p_bind(p):
    "bind : BIND ws ':'"
    p[0] = [p[1]]

def p_on(p):
    "on : ON ws event ws ':'"
    p[0] = [p[1], p[3]]

def p_separator(p):
    """separator : ws ',' ws
                 | ws ';' ws"""
    p[0] = p[2]

def p_event(p):
    """event : AL_NUM
             | temporal '(' ws AL_NUM ws ',' ws AL_NUM ws ')'"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = [p[1], p[4], p[8]]

def p_temporal(p):
    """temporal : AFTER
                | AT
                | BEFORE
                | EVERY"""
    p[0] = p[1]

def p_actions(p):
    """actions : anything actions
               | anything"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_anything(p):
    """anything : WHITESPACE
                | NEWLINE
                | AL_NUM
                | OTHER
                | ','
                | ';'
                | ':'
                | '('
                | ')'"""
    p[0] = p[1]

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line %s: %s" % (p.lineno, p.type))

lexer = lex.lex()
parser = yacc.yacc()

def parse(text, lexer=lexer):
    return parser.parse(text, lexer)
