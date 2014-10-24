#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 13:21:52 2014

@author: pavla
"""

import re, state_parser, transition_parser
from lxml import etree

class notSupportedException(Exception): pass

class invalidInputException(Exception): pass

# planarized stateflow
# states - leaf states of the state hierarchy - ssid, hierarchal name, label 
#       (in general format {"name":name, "en":entry actions, "du":during 
#       actions, "ex":exit actions}), parents, init (information whether there 
#       is default transition to this state)
# transitions - ssid (no longer unique), label (in general format 
#       {"conditions":conditions, "ca":condition actions, "ta":transition
#       actions}), source, destination, hierarchy, order (hierarchy and order
#       together define execution order - one transition has priority over 
#       another if it has lower hierarchy number, or the same hierarchy number
#       and lower order number)
#       - for a transition from a superstate there is a transition from each
#       leaf substate
#       - for  transition to a superstate there is a transition to every leaf
#       substate, such that there is default transition to this substate and
#       all its parents with lower hierarchy then the aforementioned superstate
class planarized:
    chartID = 0
    states = {}
    transitions = []

def getStateName(label):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    match = re.match(r"([^\n]*)/((.|\n)*)", labelString)
    if (match != None):
        return match.group(1).strip()
    
    match = re.match(r"([^\n]*)\n((.|\n)*)", labelString)
    if (match != None):
        return match.group(1).strip()

    return labelString

# TODO: actions, onther elements
def parseStateLabel(label):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    labelDict = {}

    # separating name and fixing rest of the label (puting "en:" on the 
    # begining if there is no action keyword)
    labelDict["name"] = getStateName(labelString)
    labelString = labelString[len(labelDict["name"]):]
    if re.match(r"(entry|during|exit|en|du|ex)", labelString) == None:
        labelString = "en:" + labelString

    actionTypes = {"entry":"en", "during":"du", "exit":"ex"}
    
    # dividing label
    labelDict["en"] = []
    labelDict["du"] = []
    labelDict["ex"] = []

    for action in state_parser.parse(labelString.strip()):
        for (actionType, abbreviation) in actionTypes.items():
            if (actionType in action[0] or abbreviation in action[0]):
                labelDict[abbreviation].append(action[1])
     
    return labelDict

def parseTransitionLabel(label):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    labelDict = {}

    m = re.match(".*?(\[(.*?\[.*?\])*.*?\])", labelString)
    if m:
        labelDict["conditions"] = m.group(1)
        labelString = labelString[m.end():]
    
    splitLabel = labelString.split("/", 1)
    if splitLabel[0] != "":
        labelDict["ca"] = splitLabel[0]
    if len(splitLabel) == 2:
        labelDict["ta"] = splitLabel[1]

    return labelDict

# for leaf state returns [(SSID of the state, listOfLabels)], otherwise
# searches all default child transitions and recursively calls itself on their
# destination and updated listOfLabels
def getDefaultPaths(stateEl, listOfLabels):
    if stateEl.find("Children") == None:
        return [(stateEl.get("SSID"), listOfLabels)]
    
    listOfPaths = []
    for trans in filter(lambda x:x.find('src/P[@Name="SSID"]') == None,
                        stateEl.findall('Children/transition')):
        dst = trans.findtext('dst/P[@Name="SSID"]')
        labelEl = trans.find('P[@Name="labelString"]')
        if (labelEl == None):
            labelDict = {}
        else:
            labelDict = parseTransitionLabel(labelEl.findtext("."))
            
        listOfPaths += getDefaultPaths(stateEl.find('Children/state[@SSID="%s"]' % dst), 
                                       listOfLabels + [labelDict])
    return listOfPaths

def makePlanarized(tree):
    stateflow = planarized()

    # TODO: find out what is chart and machine (if any of them correspond with
    #       process in DVE and what to do it there are more of them)
    stateflow.chartID = tree.find("Stateflow/machine/Children/chart").get("id")        

    # storing leaf states of the state hierarchy (ssid, name, label, parents)
    # "init" is for future information whether there is default transition
    for state in filter(lambda x:x.find("Children") == None, 
                        tree.findall("//state")):
        labelEl = state.find('P[@Name="labelString"]')
        labelDict = parseStateLabel(labelEl.findtext("."))

        parents = []
        longName = labelDict["name"]
        parent = state.getparent().getparent()
        while (parent.tag == "state"):
            parents.append(parent.get("SSID"))
            longName = getStateName(parent.find('P[@Name="labelString"]')) +\
                "_" + longName
            parent = parent.getparent().getparent()
        
        stateflow.states[state.get("SSID")] = {"longName":longName, 
        "label":labelDict, "parents":parents, "init":False}

    # setting "init"
    for trans in tree.findall("//transition"):
        srcElement = trans.find('src/P[@Name="SSID"]')
        dst = trans.findtext('dst/P[@Name="SSID"]')
        if (srcElement == None and dst in stateflow.states.keys()):
            stateflow.states[dst]["init"] = True

    stateflow.states["init"] = {"longName":"init", "label":{"name":"init"}, 
                                "parents":[], "init":True}

    # storing transitions (ssid, label, source, destination, execution order)
    # (ssid aren't unique anymore since there can be transition from superstate
    # and hence several transitions with the same ssid are created)
    for trans in tree.findall("//transition"):
        labelEl = trans.find('P[@Name="labelString"]')
        if (labelEl == None):
            labelDict = {}
        else:
            labelDict = parseTransitionLabel(labelEl.findtext("."))

        srcEl = trans.find('src/P[@Name="SSID"]')
        if (srcEl == None):
            src = "init"
        else:
            src = srcEl.findtext(".")
        dst = trans.findtext('dst/P[@Name="SSID"]')
        
        if (src == "init" and trans.getparent().getparent().tag != "chart"):
            continue

        # for transition from superstate, one transition from each substate
        # is created; for transition to superstate, transition to the substate
        # with default transition is created
        sources = []
        if (src == "init" or src in stateflow.states.keys()):
            sources.append(src)
            hierarchy = 0
        else:
            for stateSSID, state in stateflow.states.items():
                if (src in state["parents"]):
                    sources.append(stateSSID)
                    hierarchy = 1 + state["parents"].index(src)

        if (dst in stateflow.states.keys()):
            destinations = [(dst, labelDict)]
        else:
            parent = tree.find('//state[@SSID="%s"]' % dst)
            destinations = getDefaultPaths(parent, [labelDict])

        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for source in sources:
            for (destination, pathLabel) in destinations:
                stateflow.transitions.append({"ssid":trans.get("SSID"),
                "label":pathLabel, "src":source, "dst":destination,
                "hierarchy":hierarchy, "order":order})

    return stateflow
