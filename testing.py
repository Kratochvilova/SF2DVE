# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 13:17:57 2015

@author: pavla
"""

import sys, state_parser, transition_parser, action_parser, condition_parser
import planarization
from lxml import etree
from extendedExceptions import notSupportedException

def test_transition_parser(text):
    print("\nText: %s" % text)
    
    try:
        label = transition_parser.parse(text)
        print("Label: %s" % label)
    except notSupportedException as e:
        print("Label: %s" % e)
    except ValueError as e:
        print("Label: %s" % e)
    else:
        if label[0] is not None:
            print("Event: %s" % label[0])
        if label[1] is not None:
            try:
                condition = condition_parser.parse(label[1])
                print("Condition: %s" % condition)
            except ValueError as e:
                print("Condition: %s" % e)
        if label[2] is not None:
            try:
                cond_action = action_parser.parse(label[2])
                print("Condidion actions: %s\nNew variables: %s" % cond_action)
            except ValueError as e:
                print("Condition actions: %s" % e)
        if label[3] is not None:
            try:
                trans_action = action_parser.parse(label[3])
                print("Transition actions: %s\nNew variables: %s" % trans_action)
            except ValueError as e:
                print("Transition actions: %s\n" % e)

def test_state_parser(text):
    print("\nText: %s" % text)
    
    try:
        label = state_parser.parse(text)
        print("Label: %s" % label)
    except notSupportedException as e:
        print("Label: %s" % e)
    except ValueError as e:
        print("Label: %s" % e)
    else:
        for (keywordPart, actionPart) in label:
            print("%s : %s" % (keywordPart, actionPart))

def testParseStateLabel(text):
    (labelDict, labelVariables) = planarization.parseStateLabel(text, "0")
    print(labelDict)
    print(labelVariables)

def testParseTransitionLabel(text):
    (labelDict, labelVariables) = planarization.parseTransitionLabel(text, "0")
    print(labelDict)
    print(labelVariables)

def getPaths(currentPath, paths, graph):
    if currentPath[0] not in graph.values():
        return paths + [currentPath]
    else:
        for (key, value) in graph.items():
            if value == currentPath[0]:
                paths = getPaths((key, currentPath[1] + value), paths, graph)

    return paths

def main():
    #state_text1 = """en: y=0; bind: (x):=2;x =0; x++; 
    #on before(43, event) 
    #: x := 7; int i = 0; i << 2;  x+= 2* y; on sdf:bla--;"""
    #state_text2 = """brampora/ en:(x):=2;x =0; x++; du : x := 7; int i = 0; 
    #i << 2;  x+= 2* pravda; """
    #trans_text1 = """ tohle_je_muj_event_no_1  
    #[x == 6 && (y != y+2 || 30 < 7)] {x := 7; int i = 0; i << 2;  } /x =0; """
    #trans_text2 = """  [x == 6 && (y != y+2 || 30 < 7)] {x := 7; 
    #int i = 0; i << 2;  } /x =0; """

    #test_transition_parser(trans_text1)
    #test_state_parser(state_text1)
    #testParseStateLabel(state_text2)
    #testParseTransitionLabel(trans_text2)

#    graph = {'a':'i', 'b':'a', 'f':'a', 'c':'b', 'd':'b', 'e':'d', 'g':'f'}
#    print(getPaths(('a', 'i'), [], graph))

    f = open("examples/test_sf.xml", 'rb')
    stateflowEtree = etree.parse(f)
    chart = stateflowEtree.find("Stateflow/machine/Children/chart")
    labelCache = planarization.LabelCache(chart)
    p = planarization.findDefaultPaths((chart.find('.//state[@SSID="1"]'), [],[]), [], labelCache, chart)
    p2 = []
    for path in p:
        if isinstance(path[0], str):
            name = "error"
        else:
            name = planarization.getStateName(path[0].findtext('P[@Name="labelString"]'))
        p2.append((name, path[1], path[2]))
    print(p2)

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
