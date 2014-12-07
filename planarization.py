#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 13:21:52 2014

@author: pavla
"""

import re, state_parser, transition_parser, action_parser, condition_parser
from lxml import etree
from sf2dve import getDataVariable

# planarized stateflow
# states - leaf states of the state hierarchy - ssid, hierarchical name, label
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
# newVariables - variables declared in labels
class PlanarizedChart:
    chartID = 0
    chartName = ""
    states = {}
    transitions = []
    labelVariables = {}
    dataVariables = []

class LabelCache:
    chart = None    
    labels = {}
    labelVariables = {}

    def __init__(self, chart):
        self.chart = chart
    
    def _get(self, key, nodeType):
        if nodeType not in self.labels:
            self.labels[nodeType] = {}
        if key not in self.labels[nodeType]:
            label = self.chart.find('.//%s[@SSID="%s"]/P[@Name="labelString"]' 
                                             % (nodeType, key))
            if nodeType == "state":
                if label is None:
                    raise KeyError(key)
                labelString = label.findtext(".")
                (self.labels[nodeType][key], newVars) = parseStateLabel(labelString, key)

            if nodeType == "transition":
                if label is None:
                    labelString = ""
                else:
                    labelString = label.findtext(".")
                (self.labels[nodeType][key], newVars) = parseTransitionLabel(labelString, key)
            
            self.labelVariables.update(newVars)

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
    if (match is not None):
        return match.group(1).strip()
    match = re.match(r"([^\n]*)\n", labelString)
    if (match is not None):
        return match.group(1).strip()
    return labelString.strip()

# TODO: actions, other elements
def parseStateLabel(label, ssid):
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
    labelString = labelString[len(labelDict["name"]):].strip()
    if labelString != "" and re.match(r"(entry|during|exit|en|du|ex)",
                                      labelString.strip()) is None:
        labelString = "en:" + labelString

    actionTypes = {"entry":"en", "during":"du", "exit":"ex"}
    
    # dividing label
    labelDict["en"] = []
    labelDict["du"] = []
    labelDict["ex"] = []
    newVariables = {}

    parsedLabel = state_parser.parse(labelString)
    if parsedLabel is None:
        return (labelDict, newVariables)
    for (keywordPart, actionPart) in parsedLabel:
        (parsedActionPart, newVars) = action_parser.parse(actionPart, 
                                                          "state_%s_" % ssid,
                                                          newVariables)
        newVariables.update(newVars)
        parsedActionPart = parsedActionPart.strip()
        for (actionType, abbreviation) in actionTypes.items():
            if (actionType in keywordPart or abbreviation in keywordPart):
                labelDict[abbreviation].append(parsedActionPart)

    return (labelDict, newVariables)

def parseTransitionLabel(label, ssid):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    labelDict = {}
    labelDict["conditions"] = ""
    labelDict["ca"] = ""
    labelDict["ta"] = ""
    newVariables = {}

    parsedLabel = transition_parser.parse(labelString.strip())
    if parsedLabel[0] is not None and parsedLabel[0].strip() != "":
        labelDict["conditions"] = condition_parser.parse(parsedLabel[0])
        labelDict["conditions"] = labelDict["conditions"].strip()
    if parsedLabel[1] is not None and parsedLabel[1].strip() != "":
        (labelDict["ca"], newVars) = action_parser.parse(parsedLabel[1], 
                                                         "trans_%s_" % ssid,
                                                         newVariables)
        newVariables.update(newVars)
        labelDict["ca"] = labelDict["ca"].strip()
    if parsedLabel[2] is not None and parsedLabel[2].strip() != "":
        (labelDict["ta"], newVars) = action_parser.parse(parsedLabel[2], 
                                                         "trans_%s_" % ssid,
                                                         newVariables)
        newVariables.update(newVars)
        labelDict["ta"] = labelDict["ta"].strip()

    return (labelDict, newVariables)

# for leaf state returns [(SSID of the state, labelDict)], otherwise
# searches all default child transitions and recursively calls itself on their
# destination and updated listOfLabels
# TODO: correct this, especially the " and " part
def getDefaultPaths(stateEl, labelDict, labelCache):
    if stateEl.find("Children") is None:
        return [(stateEl.get("SSID"), labelDict)]
    
    listOfPaths = []
    for trans in filter(lambda x:x.find('src/P[@Name="SSID"]') is None,
                        stateEl.findall('Children/transition')):
        dst = trans.findtext('dst/P[@Name="SSID"]')
        newLabelDict = labelDict
        dstLabelDict = labelCache.getTransition(trans.get("SSID"))
        if dstLabelDict["conditions"] != "":
            newLabelDict["conditions"] += ", " + dstLabelDict["conditions"]
        if dstLabelDict["ca"] != "":
            newLabelDict["ca"] += ", " + dstLabelDict["ca"]
        if dstLabelDict["ta"] != "":
            newLabelDict["ta"] += ", " + dstLabelDict["ta"]
        listOfPaths += getDefaultPaths(stateEl.find('Children/state[@SSID="%s"]' % dst), 
                                       newLabelDict, labelCache)
    return listOfPaths

def makePlanarized(chart):
    planarizedChart = PlanarizedChart()
    labelCache = LabelCache(chart)

    planarizedChart.chartID = chart.get("id")        
    planarizedChart.chartName = chart.findtext('P[@Name="name"]')

    for varEl in chart.findall(".//data"):
        planarizedChart.dataVariables.append(getDataVariable(varEl))
    
    # storing leaf states of the state hierarchy (ssid, name, label, parents)
    # "init" is for future information whether there is default transition
    for state in filter(lambda x:x.find("Children") is None, 
                        chart.findall(".//state")):
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
        
        planarizedChart.states[stateSSID] = {
            "longName":longName, 
            "label":labelDict, 
            "parents":parents, 
            "init":False
        }

    # setting "init" - more states can have "init" set on True
    for trans in chart.findall(".//transition"):
        srcElement = trans.find('src/P[@Name="SSID"]')
        dst = trans.findtext('dst/P[@Name="SSID"]')
        if (srcElement is None and dst in planarizedChart.states.keys()):
            planarizedChart.states[dst]["init"] = True

    # initial state
    planarizedChart.states["init"] = {
        "longName":"init", 
        "label":{"name":"init", "en":"", "du":"", "ex":""}, 
        "parents":[], 
        "init":True
    }

    # storing transitions (ssid, label, source, destination, execution order)
    # (ssid aren't unique anymore since there can be transition from superstate
    # and hence several transitions with the same ssid are created)
    for trans in chart.findall(".//transition"):
        labelDict = labelCache.getTransition(trans.get("SSID"))

        srcEl = trans.find('src/P[@Name="SSID"]')
        if (srcEl is None):
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
        if (src == "init" or src in planarizedChart.states.keys()):
            sources.append(src)
        else:
            for stateSSID, state in planarizedChart.states.items():
                if (src in state["parents"]):
                    sources.append(stateSSID)

        if (dst in planarizedChart.states.keys()):
            destinations = [(dst, labelDict)]
        else:
            parent = chart.find('.//state[@SSID="%s"]' % dst)
            destinations = getDefaultPaths(parent, labelDict, labelCache)
        
        # determining hierarchy, orderType and order        
        if src == "init":
            hierarchy = 0
            orderType = 0
        else:
            hierarchy = 1
            srcState = chart.find('.//state[@SSID="%s"]' % src)
            srcParent = srcState.getparent().getparent()
            while srcParent.tag != "chart":
                hierarchy += 1
                srcParent = srcParent.getparent().getparent()
                
            orderType = 2
            dstState = chart.find('.//state[@SSID="%s"]' % dst)
            dstParent = dstState.getparent().getparent()
            while dstParent.tag != "chart":
                if dstParent.get("SSID") == src:
                    orderType = 1
                dstParent = dstParent.getparent().getparent()
        
        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for source in sources:
            for (destination, tempLabelDict) in destinations:
                planarizedChart.transitions.append({"ssid":trans.get("SSID"),
                "label":tempLabelDict, "src":source, "dst":destination,
                "hierarchy":hierarchy, "orderType":orderType, "order":order})
    
    planarizedChart.labelVariables = labelCache.labelVariables
    
    return planarizedChart
