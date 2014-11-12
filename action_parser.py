#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  9 09:35:20 2014

@author: pavla
"""

from ply import lex, yacc

newVars = []

keywords =  {
   "char" : "CHAR",
   "int" : "INT",
   "long" : "LONG",
   "short" : "SHORT",
   "signed" : "SIGNED",
   "unsigned" : "UNSIGNED",
   "void" : "VOID"
}

tokens = (["COMMENT", "RIGHT_ASSIGN", "LEFT_ASSIGN", "ADD_ASSIGN", 
           "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN", 
           "AND_ASSIGN", "XOR_ASSIGN", "OR_ASSIGN", "RIGHT_OP", "LEFT_OP", 
           "INC_OP", "DEC_OP", "AND_OP", "OR_OP", "LE_OP", "GE_OP", "EQ_OP", 
           "NE_OP", "LBRACE", "RBRACE", "LBRACKET", "RBRACKET", "NUMBER",
           "IDENTIFIER"] + list(keywords.values()))

literals = ";,:=()&!~-+*/%<>^|?"

t_ignore = " \t\n\r\f\v"
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

def t_COMMENT(t):
    r"(//.*)|(/\*(.|\n)*?\*/)"
    pass

def t_IDENTIFIER(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"
    t.type = keywords.get(t.value, "IDENTIFIER")
    return t

def t_error(t):
    raise TypeError("Unknown text '%s'" % t.value)

def p_start(p):
    """start : empty
             | block_items"""
    p[0] = p[1]

def p_empty(p):
    "empty :"
    pass

def p_compound_statement(p):
    """compound_statement : LBRACE RBRACE
                          | LBRACE block_items RBRACE"""
    if len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1] + p[2] + p[3]

def p_block_items(p):
    """block_items : declaration block_items
                   | statement block_items
                   | declaration
                   | statement"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2]

def p_declaration(p):
    """declaration : type_specifiers ';'
                   | type_specifiers init_declarator_list ';'"""
    if len(p) == 2:
        p[0] = p[1] + ' ' + p[2]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]
        newVars.append((p[1], p[2]))

def p_type_specifiers(p):
    """type_specifiers : type_specifier
                       | type_specifier type_specifiers """
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2]

def p_type_specifier(p):
    """type_specifier : VOID
                      | CHAR
                      | SHORT
                      | INT
                      | LONG
                      | SIGNED
                      | UNSIGNED"""
    p[0] = p[1]

def p_init_declarator_list(p):
    """init_declarator_list : init_declarator
                            | init_declarator ',' init_declarator_list"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2] + ' ' + p[3]

def p_init_declarator(p):
    """init_declarator : declarator '=' initializer
                       | declarator"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + ' ' + p[2] + ' ' + p[3]

def p_declarator(p):
    """declarator : IDENTIFIER
                  | '(' declarator ')'
                  | declarator LBRACKET assignment_expression RBRACKET
                  | declarator LBRACKET RBRACKET"""
    if len(p) == 2:
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
    elif len(p) == 4:
        p[0] = p[1] + p[2] + p[3]
    else:
        p[0] = p[1] + p[2] + p[4] 

def p_initializer_list(p):
    """initializer_list : initializer
                        | initializer ','
                        | initializer ',' initializer_list"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2] + ' ' + p[3]

def p_statement(p):
    """statement : labeled_statement
                 | compound_statement
                 | expression_statement"""
    p[0] = p[1]

def p_labeled_statement(p):
    """labeled_statement : IDENTIFIER ':' statement"""
    p[0] = p[1] + p[2] + p[3]
    

def p_expression_statement(p):
    """expression_statement : ';'
                            | expression ';'"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_expression(p):
    """expression : assignment_expression
                  | expression ',' assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2] + ' ' + p[3]

def p_assignment_expression(p):
    """assignment_expression : logical_or_expression
                | unary_expression assignment_operator assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    elif p[2] == '=':
        p[0] = p[1] + ' = ' + p[3]
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
    

def p_assignment_operator(p):
    """assignment_operator : '='
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
    """unary_expression : postfix_expression
                        | INC_OP unary_expression
                        | DEC_OP unary_expression
                        | unary_operator unary_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_unary_operator(p):
    """unary_operator : '+'
                      | '-'
                      | '~'
                      | '!'"""
    p[0] = p[1]

def p_postfix_expression(p):
    """postfix_expression : primary_expression
                          | postfix_expression LBRACKET expression RBRACKET
                          | postfix_expression INC_OP
                          | postfix_expression DEC_OP"""
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = p[1] + p[2]
    else: 
        p[0] = p[1] + p[2] + p[3] + p[4]

def p_primary_expression(p):
    """primary_expression : IDENTIFIER
                          | NUMBER
                          | '(' expression ')'"""
    if len(p) == 2:
        p[0] = p[1]
    else: 
        p[0] = p[1] + p[2] + p[3]

def p_error(p):
    if p is None:
        raise ValueError("Unknown error")
    raise ValueError("Syntax error, line {0}: {1}".format(p.lineno, p.type))

lexer = lex.lex()
parser = yacc.yacc()

text = """
//ok, this is really cute c program :D
int i = 20, j, k = 30;
char c = 4;
int pole[8] = {0, 1, 2, 3, 4, 5, 6};

pole[1] = i;
/* I changed my mind, I don't wanna assign some weird number there
pole[2] = j; */
pole[3] *= (2 + k) / 4;
pole[4] = c;
pole[5] = c * k % j;
pole[5] = 0 && 1;
/*boooo*/
"""

#lexer.input(text)
#while True:
#    tok = lexer.token()
#    if not tok: break      # No more input
#    print(tok)

print(parser.parse(text, lexer))

print(newVars)