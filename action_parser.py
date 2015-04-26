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
Created on Sun Nov  9 09:35:20 2014

@author: pavla
"""

from ply import lex, yacc
import os

newVars = None
prefix = None
typeConversions = {
    "int":["int", "int16", "int32", "uint8", "uint16", "uint32"],
    "byte":["bool", "char", "int8"],
    "modifiers":["long", "short", "signed", "unsigned"]
}

keywords =  {
    "const" : "CONST",
    "bool" : "BOOL",
    "char" : "CHAR",
    "int" : "INT",
    "long" : "LONG",
    "short" : "SHORT",
    "signed" : "SIGNED",
    "unsigned" : "UNSIGNED",
    "int8" : "INT8",
    "int16" : "INT16",
    "int32" : "INT32",
    "uint8" : "UINT8",
    "uint16" : "UINT16",
    "uint32" : "UINT32"
}

tokens = (["COLON_ASSIGN", "RIGHT_ASSIGN", "LEFT_ASSIGN", "ADD_ASSIGN",
           "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN",
           "AND_ASSIGN", "XOR_ASSIGN", "OR_ASSIGN", "RIGHT_OP", "LEFT_OP",
           "INC_OP", "DEC_OP", "AND_OP", "OR_OP", "LE_OP", "GE_OP", "EQ_OP",
           "NE_OP", "LBRACE", "RBRACE", "LBRACKET", "RBRACKET", "NUMBER",
           "IDENTIFIER", "NEWLINE"] + list(keywords.values()))

literals = ";,:=()&!~-+*/%<>^|?@"

t_ignore = " \t\r\f\v"
t_ignore_COMMENT = r"(//.*)|(/\*(.|\n)*?\*/)"
t_COLON_ASSIGN = r":="
t_RIGHT_ASSIGN = r">>="
t_LEFT_ASSIGN = r"<<="
t_ADD_ASSIGN = r"\+="
t_SUB_ASSIGN = r"-="
t_MUL_ASSIGN = r"\*="
t_DIV_ASSIGN = r"/="
t_MOD_ASSIGN = r"%="
t_AND_ASSIGN = r"&="
t_XOR_ASSIGN = r"^="
t_OR_ASSIGN = r"\|="
t_RIGHT_OP = r">>"
t_LEFT_OP = r"<<"
t_INC_OP = r"\+\+"
t_DEC_OP = r"--"
t_AND_OP = r"&&"
t_OR_OP = r"\|\|"
t_LE_OP = r"<="
t_GE_OP = r">="
t_EQ_OP = r"=="
t_NE_OP = r"!="
t_LBRACE = r"({|<%)"
t_RBRACE = r"(}|%>)"
t_LBRACKET = r"(\[|<:)"
t_RBRACKET = r"(\]|:>)"
t_NUMBER = r"[0-9]+"

def t_IDENTIFIER(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"
    t.type = keywords.get(t.value, "IDENTIFIER")
    return t

def t_NEWLINE(t):
    r"\n"
    t.lexer.lineno += 1
    return t

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_start(p):
    """start : empty
             | block_items"""
    if p[1] is None:
        p[0] = []
    else:
        p[0] = p[1]

def p_empty(p):
    "empty :"
    pass

def p_compound_statement(p):
    """compound_statement : LBRACE RBRACE
                          | LBRACE block_items RBRACE"""
    if len(p) == 4:
        p[0] = p[2]

def p_block_items(p):
    """block_items : declaration block_items
                   | statement block_items
                   | declaration
                   | statement"""
    if isinstance(p[1], str):
        p[1] = [p[1]]
    if len(p) == 3:
        if p[1] is None:
            p[0] = p[2]
        else:
            p[0] = p[1] + p[2]
    else:
        if p[1] is None:
            p[0] = []
        else:
            p[0] = p[1]

def p_declaration(p):
    """declaration : type_specifiers ';'
                   | type_specifiers init_declarator_list ';'
                   | type_specifiers NEWLINE
                   | type_specifiers init_declarator_list NEWLINE"""
    if len(p) == 4:
        const = False
        tempType = None
        for varType in p[1]:
            if varType == "const":
                const = True

            elif tempType == None:
                if varType in typeConversions["byte"]:
                    tempType = varType
                else:
                    tempType = "int"

            elif (tempType == "int" and
                  varType not in typeConversions["modifiers"]):
                      raise ValueError("Error in declaration specifiers")

            elif tempType == "bool":
                raise ValueError("Error in declaration specifiers")

            elif tempType == "byte":
                if varType == "signed":
                    pass
                elif varType == "unsigned":
                    tempType = "int"
                else:
                    raise ValueError("Error in declaration specifiers")

        if tempType == "int":
            finalType = "int"
        elif tempType in typeConversions["byte"]:
            finalType = "byte"

        for varInit in p[2]:
            newVars[prefix + varInit[0]] = {"type":finalType, "const":const,
                                            "init":varInit[1], "scope":"label"}

def p_type_specifiers(p):
    """type_specifiers : type_specifier
                       | type_specifier type_specifiers """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[2] + [p[1]]

def p_type_specifier(p):
    """type_specifier : CONST
                      | BOOL
                      | CHAR
                      | SHORT
                      | INT
                      | LONG
                      | SIGNED
                      | UNSIGNED
                      | INT8
                      | INT16
                      | INT32
                      | UINT8
                      | UINT16
                      | UINT32"""
    p[0] = p[1]

def p_init_declarator_list(p):
    """init_declarator_list : init_declarator
                            | init_declarator ',' init_declarator_list"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_init_declarator(p):
    """init_declarator : declarator '=' initializer
                       | declarator"""
    if len(p) == 2:
        p[0] = (p[1], None)
    else:
        p[0] = (p[1], p[3])

def p_declarator(p):
    """declarator : IDENTIFIER
                  | '(' declarator ')'
                  | declarator LBRACKET assignment_expression RBRACKET
                  | declarator LBRACKET RBRACKET"""
    if len(p) == 2:
        if prefix + p[1] in newVars:
            p[1] = prefix + p[1]
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = p[1] + p[2] + p[3]
    else:
        p[0] = p[1] + p[2] + p[3] + p[4]

def p_initializer(p):
    """initializer : LBRACE initializer_list RBRACE
                   | assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2] + p[3]

def p_initializer_list(p):
    """initializer_list : initializer
                        | initializer ','
                        | initializer ',' initializer_list"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2] + ' ' + p[3]

def p_statement(p):
    """statement : compound_statement
                 | expression_statement"""
    p[0] = p[1]

def p_expression_statement(p):
    """expression_statement : ';'
                            | expression ';'
                            | NEWLINE
                            | expression NEWLINE"""
    if len(p) == 3:
        p[0] = p[1]

def p_expression(p):
    """expression : assignment_expression
                  | expression ',' assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ', ' + p[3]

def p_assignment_expression(p):
    """assignment_expression : inc_dec_assignment
            | logical_or_expression
            | unary_expression assignment_operator assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    elif p[2] == '=':
        p[0] = p[1] + ' = ' + p[3]
    elif p[2] == ':=':
        p[0] = p[1] + ' = ' + p[3]
    elif p[2] == "+=":
        p[0] = p[1] + ' = (' + p[1] + ') + (' + p[3] + ')'
    elif p[2] == "-=":
        p[0] = p[1] + ' = (' + p[1] + ') - (' + p[3] + ')'
    elif p[2] == "*=":
        p[0] = p[1] + ' = (' + p[1] + ') * (' + p[3] + ')'
    elif p[2] == "/=":
        p[0] = p[1] + ' = (' + p[1] + ') / (' + p[3] + ')'
    elif p[2] == "%=":
        p[0] = p[1] + ' = (' + p[1] + ') % (' + p[3] + ')'
    elif p[2] == "&=":
        p[0] = p[1] + ' = (' + p[1] + ') & (' + p[3] + ')'
    elif p[2] == "^=":
        p[0] = p[1] + ' = (' + p[1] + ') ^ (' + p[3] + ')'
    elif p[2] == "|=":
        p[0] = p[1] + ' = (' + p[1] + ') | (' + p[3] + ')'
    elif p[2] == ">>=":
        p[0] = p[1] + ' = (' + p[1] + ') >> (' + p[3] + ')'
    elif p[2] == "<<=":
        p[0] = p[1] + ' = (' + p[1] + ') << (' + p[3] + ')'
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_inc_dec_assignment(p):
    """inc_dec_assignment : INC_OP unary_expression
                          | unary_expression INC_OP
                          | DEC_OP unary_expression
                          | unary_expression DEC_OP"""
    if p[1] == "++":
        p[0] = p[2] + " = " + p[2] + " + 1"
    elif p[2] == "++":
        p[0] = p[1] + " = " + p[1] + " + 1"
    elif p[1] == "--":
        p[0] = p[2] + " = " + p[2] + " - 1"
    elif p[2] == "--":
        p[0] = p[1] + " = " + p[1] + " - 1"

def p_assignment_operator(p):
    """assignment_operator : '='
                           | COLON_ASSIGN
                           | MUL_ASSIGN
                           | DIV_ASSIGN
                           | MOD_ASSIGN
                           | ADD_ASSIGN
                           | SUB_ASSIGN
                           | LEFT_ASSIGN
                           | RIGHT_ASSIGN
                           | AND_ASSIGN
                           | XOR_ASSIGN
                           | OR_ASSIGN"""
    p[0] = p[1]

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
                        | primary_expression LBRACKET expression RBRACKET"""
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
                          | '(' expression ')'"""
    if len(p) == 2:
        if prefix + p[1] in newVars:
            p[1] = prefix + p[1]
        p[0] = p[1]
    else: 
        p[0] = p[1] + p[2] + p[3]

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line %s: %s" % (p.lineno, p.type))

directory = os.path.join(os.path.dirname(__file__), 
                         "parser_tables", 
                         os.path.basename(__file__).rsplit('.', 1)[0])
try:
    os.makedirs(directory, exist_ok=True)
except OSError:
    pass

lexer = lex.lex(debug=False, optimize=True, outputdir=directory)
parser = yacc.yacc(debug=False, optimize=True, outputdir=directory)

def parse(text, tempPrefix="", variables={}, lexer=lexer):    
    global prefix
    global newVars
    prefix = tempPrefix
    newVars = variables
    return (parser.parse(text, lexer), newVars)
