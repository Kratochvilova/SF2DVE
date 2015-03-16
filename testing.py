# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 13:17:57 2015

@author: pavla
"""

import sys, state_parser, transition_parser, action_parser, condition_parser
from extendedExceptions import notSupportedException

def test_transition_labels(text):
    print("\nText: %s\n" % text)
    
    try:
        label = transition_parser.parse(text)
        print("Label: %s\n" % label)
    except notSupportedException as e:
        print("Label: %s\n" % e)
    except ValueError as e:
        print("Label: %s\n" % e)
    else:
        if label[0] is not None:
            print("Event: %s" % label[0])
        if label[1] is not None:
            try:
                condition = condition_parser.parse(label[1])
                print("Condition: %s" % condition)
            except ValueError as e:
                print("Condition: %s\n" % e)
        if label[2] is not None:
            try:
                cond_action = action_parser.parse(label[2])
                print("Condidion actions: %s\nNew variables: %s" % cond_action)
            except ValueError as e:
                print("Condition actions: %s\n" % e)
        if label[3] is not None:
            try:
                trans_action = action_parser.parse(label[3])
                print("Transition actions: %s\nNew variables: %s" % trans_action)
            except ValueError as e:
                print("Transition actions: %s\n" % e)

def test_state_labels(text):
    print("\nText: %s\n" % text)
    
    try:
        label = state_parser.parse(text)
        print("Label: %s\n" % label)
    except notSupportedException as e:
        print("Label: %s\n" % e)
    except ValueError as e:
        print("Label: %s\n" % e)
    else:
        for (keywords, action_string) in label:
            keys = []
            for key in keywords:
                if isinstance(key, str):
                    keys.append(key)
                elif isinstance(key[1], str):
                    keys.append("%s[%s]" % (key[0], key[1]))
                else:
                    keys.append("%s[%s(%s,%s)]" % (key[0], key[1][0], key[1][1], key[1][2]))
            print("Keys: %s" % (", ").join(keys))
            try:
                actions = action_parser.parse(action_string)
                print("Actions: %s\n" % actions[0])
            except ValueError as e:
                print("Actions: %s\n" % e)

def main():
    transition_text = """ tohle_je_muj_event_no_1  
    [x == 6 && (y != y+2 || 30 < 7)] {x := 7; int i = 0; i << 2;  } /x =0; """
    state_text = """en, bind: (x):=2;x =0; x++; on before(43, event),  
    entry: x := 7; int i = 0; i << 2;  x+= 2* pravda; on sdf:bla = bla;"""
    
    test_transition_labels(transition_text)    
    test_state_labels(state_text)

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
