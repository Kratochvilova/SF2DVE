#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 13:21:52 2014

@author: pavla
"""

import re, state_parser, transition_parser, action_parser, condition_parser
from sf2dve import getDataVariable
from exceptions import invalidInputException

# planarized Stateflow chart
# states - leaf states of the state hierarchy - ssid = {hierarchical name,
#       label(in general format {"name":name, "en":entry actions, "du":during
#       actions, "ex":exit actions}), parents}
# transitions - ssid (no longer unique), label (in general format
#       {"conditions":conditions, "ca":condition actions, "ta":transition
#       actions}), source, destination, srcHierarchy, transType, order (hierarchy,
#       transType and order together define execution order - it is determined
#       first by srcHierarchy, then by transType and then by order; in all
#       cases lower number means higher priority)
# variables - name = {"type":variable type, "const":True or False,
#       "init":initialization, "scope":label, local  or input}
class PlanarizedChart:
    chartID = 0
    chartName = ""
    states = {}
    transitions = []
    variables = {}

# labels - parsed labels of states and transitions
# labelVariables - variables declared in labels
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
            labelEl = self.chart.find('.//%s[@SSID="%s"]/P[@Name="labelString"]'
                                      % (nodeType, key))
            if nodeType == "state":
                if labelEl is None:
                    raise KeyError(key)
                labelString = labelEl.findtext(".")
                (self.labels[nodeType][key], newVars) = parseStateLabel(labelString, key)

            if nodeType == "transition":
                if labelEl is None:
                    labelString = ""
                else:
                    labelString = labelEl.findtext(".")
                (self.labels[nodeType][key], newVars) = parseTransitionLabel(labelString, key)

            self.labelVariables.update(newVars)

        return self.labels[nodeType][key]

    def getState(self, key):
        return self._get(key, "state")

    def getTransition(self, key):
        return self._get(key, "transition")
        
def getStateName(labelString):
    match = re.match(r"([^\n]*)/", labelString)
    if (match is not None):
        return match.group(0)
    match = re.match(r"([^\n]*)\n", labelString)
    if (match is not None):
        return match.group(0)
    return labelString

def parseStateLabel(labelString, ssid):
    labelDict = {}

    # separating name and fixing rest of the label (puting "en:" on the
    # begining if there is no action keyword)
    labelDict["name"] = getStateName(labelString)
    labelString = labelString[len(labelDict["name"]):].strip()
    labelDict["name"] = labelDict["name"].strip()
    if labelString != "" and re.match(r"(entry|during|exit|en|du|ex)",
                                      labelString.strip()) is None:
        labelString = "en:" + labelString

    actionTypes = {"entry":"en", "during":"du", "exit":"ex"}

    # dividing label
    labelDict["en"] = []
    labelDict["du"] = []
    labelDict["ex"] = []
    labelVariables = {}

    parsedLabel = state_parser.parse(labelString)
    if parsedLabel is None:
        return (labelDict, labelVariables)
    for (keywordPart, actionPart) in parsedLabel:
        (parsedActionPart, newVars) = action_parser.parse(actionPart,
                                                          "state_%s_" % ssid,
                                                          labelVariables)
        labelVariables.update(newVars)
        parsedActionPart = parsedActionPart.strip()
        for (actionType, abbreviation) in actionTypes.items():
            if (actionType in keywordPart or abbreviation in keywordPart):
                labelDict[abbreviation].append(parsedActionPart)

    return (labelDict, labelVariables)

def parseTransitionLabel(labelString, ssid):
    labelDict = {}
    labelDict["conditions"] = ""
    labelDict["ca"] = ""
    labelDict["ta"] = []
    labelVariables = {}

    parsedLabel = transition_parser.parse(labelString.strip())
    if parsedLabel[0] is not None and parsedLabel[0].strip() != "":
        labelDict["conditions"] = condition_parser.parse(parsedLabel[0])
        labelDict["conditions"] = labelDict["conditions"].strip()
    if parsedLabel[1] is not None and parsedLabel[1].strip() != "":
        (labelDict["ca"], newVars) = action_parser.parse(parsedLabel[1],
                                                         "trans_%s_" % ssid,
                                                         labelVariables)
        labelVariables.update(newVars)
        labelDict["ca"] = labelDict["ca"].strip()
    if parsedLabel[2] is not None and parsedLabel[2].strip() != "":
        (ta, newVars) = action_parser.parse(parsedLabel[2], "trans_%s_" % ssid,
                                            labelVariables)
        labelVariables.update(newVars)
        labelDict["ta"].append(ta.strip())

    return (labelDict, labelVariables)

def addState(stateEl, labelCache, planarizedChart):
    stateSSID = stateEl.get("SSID")
    labelDict = labelCache.getState(stateSSID)

    parents = []
    longName = labelDict["name"]
    parent = stateEl.getparent().getparent()
    while (parent.tag == "state"):
        parentSSID = parent.get("SSID")
        parents.append(parentSSID)
        parentDict = labelCache.getState(parentSSID)
        longName = parentDict["name"] + "_" + longName
        labelDict["du"] = parentDict["du"] + labelDict["du"]
        parent = parent.getparent().getparent()

    planarizedChart.states[stateSSID] = {
        "longName":longName,
        "label":labelDict,
        "parents":parents,
        "superstate":False
    }

def findDefaultDestination(dst, chart, planarizedChart):
    parentSSID = dst
    parentEl = chart.find('.//state[@SSID="%s"]' % parentSSID)

    while parentSSID not in planarizedChart.states:
        transitions = parentEl.findall('Children/transition')
        defaultTrans = []
        for trans in transitions:
            if (trans.find('src/P[@Name="SSID"]') is None and
                trans.findtext('P[@Name="executionOrder"]') == "1"):
                    defaultTrans.append(trans)
        if len(defaultTrans) != 1:
            print(parentSSID)
            raise invalidInputException("Wrong number of default transitions.")
        else:
            parentSSID = defaultTrans[0].findtext('dst/P[@Name="SSID"]')
            parentEl = chart.find('.//state[@SSID="%s"]' % parentSSID)

    return parentSSID

def makePlanarized(chart):
    planarizedChart = PlanarizedChart()
    labelCache = LabelCache(chart)

    planarizedChart.chartID = chart.get("id")
    planarizedChart.chartName = chart.findtext('P[@Name="name"]')

    # storing variables (defined as data, not in labels)
    for varEl in chart.findall(".//data"):
        (varName, varDef) = getDataVariable(varEl)
        planarizedChart.variables[varName] = varDef

    # storing states (ssid, hierarchical name, label, parents)
    # superstates are stored only if they contain labeled default transition
    for stateEl in chart.findall(".//state"):
        if stateEl.find("Children") is None:
            addState(stateEl, labelCache, planarizedChart)
        else:
            defaultTrans = filter(lambda x:x.find('src/P[@Name="SSID"]') is None,
                                  stateEl.findall('Children/transition'))
            for trans in defaultTrans:
                if (trans.find('P[@Name="labelString"]') is not None and
                    trans.findtext('P[@Name="labelString"]').strip() != ""):
                        addState(stateEl, labelCache, planarizedChart)
                        planarizedChart.states[stateEl.get("SSID")]["superstate"] = True
                        break

    # initial state
    planarizedChart.states["start"] = {
        "longName":"start",
        "label":{"name":"start", "en":"", "du":"", "ex":""},
        "parents":[],
        "superstate":False
    }

    # storing transitions (ssid, label, source, destination, execution order)
    # (ssid aren't unique anymore, since there can be transition from 
    # superstate and hence several transitions with the same ssid are created)
    # transition label must also contain actions of crossed superstates
    for trans in chart.findall(".//transition"):
        labelDict = labelCache.getTransition(trans.get("SSID"))
        transParent = trans.getparent().getparent()
        srcEl = trans.find('src/P[@Name="SSID"]')
        if (srcEl is None):
            src = "init"
        else:
            src = srcEl.findtext(".")
        dst = trans.findtext('dst/P[@Name="SSID"]')

        # not labeled default transitions are ignored (except the one main)
        if (src == "init" and transParent.tag != "chart" and
            (trans.find('P[@Name="labelString"]') is None or
            trans.findtext('P[@Name="labelString"]').strip() == "")):
                continue

        # for transition from superstate, one transition from each substate
        # is created; for transition to superstate, transition to the substate
        # with default transition is created or to a superstate, if there are
        # labeled default transitions
        sources = []
        if src == "init" and transParent.tag == "chart":
            sources.append("start")
        elif src == "init":
            sources.append(transParent.get("SSID"))
        elif (src in planarizedChart.states and 
              not planarizedChart.states[src]["superstate"]):
            sources.append(src)
        else:
            for stateSSID, state in planarizedChart.states.items():
                if not state["superstate"] and src in state["parents"]:
                    sources.append(stateSSID)

        if dst in planarizedChart.states:
            destination = dst
        else:
            destination = findDefaultDestination(dst, chart, planarizedChart)

        # updating transition action by actions of crossed superstates
        # (sources have the same parents)
        transHierarchy = 0
        transAncestor = transParent
        while transAncestor.tag != "chart":
            transHierarchy += 1
            transAncestor = transAncestor.getparent().getparent()
        if src != "init":
            for parentSSID in list(reversed(planarizedChart.states[sources[0]]["parents"]))[transHierarchy:]:
                parentLabel = labelCache.getState(parentSSID)
                labelDict["ta"] = parentLabel["ex"] + labelDict["ta"]
            for parentSSID in list(reversed(planarizedChart.states[destination]["parents"]))[transHierarchy:]:
                parentLabel = labelCache.getState(parentSSID)
                labelDict["ta"] = labelDict["ta"] + parentLabel["en"]

        # determining source hierarchy, transition type and order
        if sources[0] == "start":
            srcHierarchy = 0
        else:
            srcHierarchy = 1
            if src == "init":
                srcState = chart.find('.//state[@SSID="%s"]' % sources[0])
            else:
                srcState = chart.find('.//state[@SSID="%s"]' % src)
            srcParent = srcState.getparent().getparent()
            while srcParent.tag != "chart":
                srcHierarchy += 1
                srcParent = srcParent.getparent().getparent()

        if transParent.get("SSID") == src:
            transType = 2
        elif src == "init":
            transType = 0
        else:
            transType = 1

        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for source in sources:
            planarizedChart.transitions.append({"ssid":trans.get("SSID"),
            "label":labelDict, "src":source, "dst":destination,
            "srcHierarchy":srcHierarchy, "transType":transType, 
            "order":order})

    planarizedChart.variables.update(labelCache.labelVariables)

    return planarizedChart
