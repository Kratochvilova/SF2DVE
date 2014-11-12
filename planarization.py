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
#       actions}), source, destination, hierarchy, orderType, order (hierarchy,
#       orderType and order together define execution order - it is determined
#       first by hierarchy number then by orderType and then by order; in all
#       cases lower number means higher priority)
#       - for a transition from a superstate there is a transition from each
#       leaf substate
#       - for  transition to a superstate there is a transition to every leaf
#       substate, such that there is default transition to this substate and
#       all its parents with lower hierarchy then the aforementioned superstate
class Planarized:
    chartID = 0
    states = {}
    transitions = []
    
class LabelCache:
    labels = {}
    stateflowEtree = None

    def __init__(self, stateflowEtree):
        self.stateflowEtree = stateflowEtree
    
    def _get(self, key, nodeType):
        if nodeType not in self.labels:
            self.labels[nodeType] = {}
        if key not in self.labels[nodeType]:
            label = self.stateflowEtree.find('//%s[@SSID="%s"]'
            '/P[@Name="labelString"]' % (nodeType, key))
            if nodeType == "state":
                if label == None:
                    raise KeyError(key)
                labelString = label.findtext(".")
                self.labels[nodeType][key] = parseStateLabel(labelString)
            if nodeType == "transition":
                if label == None:
                    labelString = ""
                else:
                    labelString = label.findtext(".")
                self.labels[nodeType][key] = parseTransitionLabel(labelString)
        return self.labels[nodeType][key]
    
    def getState(self, key):
        return self._get(key, "state")
        
    def getTransition(self, key):
        return self._get(key, "transition")

def getStateName(label):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    match = re.match(r"([^\n]*)/", labelString)
    if (match != None):
        return match.group(1).strip()
    match = re.match(r"([^\n]*)\n", labelString)
    if (match != None):
        return match.group(1).strip()
    return labelString

# TODO: actions, other elements
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
    if labelString != "" and re.match(r"(entry|during|exit|en|du|ex)", 
                                      labelString.strip()) == None:
        labelString = "en:" + labelString

    actionTypes = {"entry":"en", "during":"du", "exit":"ex"}
    
    # dividing label
    labelDict["en"] = []
    labelDict["du"] = []
    labelDict["ex"] = []

    parsedLabel = state_parser.parse(labelString.strip())
    if parsedLabel == None:
        return labelDict
    for (keywordPart, actionPart) in parsedLabel:
        for (actionType, abbreviation) in actionTypes.items():
            if (actionType in keywordPart or abbreviation in keywordPart):
                labelDict[abbreviation].append(actionPart)
    
    return labelDict

def parseTransitionLabel(label):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    labelDict = {}

    parsedLabel = transition_parser.parse(labelString.strip())
    if parsedLabel[0] != None:
        labelDict["conditions"] = [parsedLabel[0]]
    if parsedLabel[1] != None:
        labelDict["ca"] = [parsedLabel[1]]
    if parsedLabel[2] != None:
        labelDict["ta"] = [parsedLabel[2]]

    return labelDict

# for leaf state returns [(SSID of the state, labelDict)], otherwise
# searches all default child transitions and recursively calls itself on their
# destination and updated listOfLabels
def getDefaultPaths(stateEl, listOfLabels, labelCache):
    if stateEl.find("Children") == None:
        return [(stateEl.get("SSID"), listOfLabels)]
    
    listOfPaths = []
    for trans in filter(lambda x:x.find('src/P[@Name="SSID"]') == None,
                        stateEl.findall('Children/transition')):
        dst = trans.findtext('dst/P[@Name="SSID"]')
        listOfLabels.append(labelCache.getTransition(trans.get("SSID")))
        
        listOfPaths += getDefaultPaths(stateEl.find('Children/state[@SSID="%s"]' % dst), 
                                       listOfLabels, labelCache)
    return listOfPaths

def makePlanarized(stateflowEtree):
    stateflow = Planarized()
    labelCache = LabelCache(stateflowEtree)

    # TODO: find out what is chart and machine (if any of them correspond with
    #       process in DVE and what to do it there are more of them)
    stateflow.chartID = stateflowEtree.find("Stateflow/machine/Children/chart").get("id")        

    # storing leaf states of the state hierarchy (ssid, name, label, parents)
    # "init" is for future information whether there is default transition
    for state in filter(lambda x:x.find("Children") == None, 
                        stateflowEtree.findall("//state")):
        stateSSID = state.get("SSID")
        labelDict = labelCache.getState(stateSSID)
        
        parents = []
        longName = labelDict["name"]
        parent = state.getparent().getparent()
        while (parent.tag == "state"):
            parentSSID = parent.get("SSID")
            parents.append(parentSSID)
            parentDict = labelCache.getState(parentSSID)
            longName = parentDict["name"] + "_" + longName
            labelDict["en"] = parentDict["en"] + labelDict["en"]
            labelDict["ex"] = labelDict["ex"] + parentDict["ex"]
            parent = parent.getparent().getparent()
        
        stateflow.states[stateSSID] = {"longName":longName, 
        "label":labelDict, "parents":parents, "init":False}

    # setting "init" - more states can have "init" set on True
    for trans in stateflowEtree.findall("//transition"):
        srcElement = trans.find('src/P[@Name="SSID"]')
        dst = trans.findtext('dst/P[@Name="SSID"]')
        if (srcElement == None and dst in stateflow.states.keys()):
            stateflow.states[dst]["init"] = True

    # initial state
    stateflow.states["init"] = {"longName":"init", "label":{"name":"init"}, 
                                "parents":[], "init":True}

    # storing transitions (ssid, label, source, destination, execution order)
    # (ssid aren't unique anymore since there can be transition from superstate
    # and hence several transitions with the same ssid are created)
    for trans in stateflowEtree.findall("//transition"):
        labelDict = labelCache.getTransition(trans.get("SSID"))

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
        else:
            for stateSSID, state in stateflow.states.items():
                if (src in state["parents"]):
                    sources.append(stateSSID)

        if (dst in stateflow.states.keys()):
            destinations = [(dst, [labelDict])]
        else:
            parent = stateflowEtree.find('//state[@SSID="%s"]' % dst)
            destinations = getDefaultPaths(parent, [labelDict], labelCache)
        
        # determining hierarchy, orderType and order        
        if src == "init":
            hierarchy = 0
            orderType = 0
        else:
            hierarchy = 1
            srcState = stateflowEtree.find('//state[@SSID="%s"]' % src)
            srcParent = srcState.getparent().getparent()
            while srcParent.tag != "chart":
                hierarchy += 1
                srcParent = srcParent.getparent().getparent()
                
            orderType = 2
            dstState = stateflowEtree.find('//state[@SSID="%s"]' % dst)
            dstParent = dstState.getparent().getparent()
            while dstParent.tag != "chart":
                if dstParent.get("SSID") == src:
                    orderType = 1
                dstParent = dstParent.getparent().getparent()
        
        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for source in sources:
            for (destination, listOfLabels) in destinations:
                stateflow.transitions.append({"ssid":trans.get("SSID"),
                "label":listOfLabels, "src":source, "dst":destination,
                "hierarchy":hierarchy, "orderType":orderType, "order":order})

    return stateflow
