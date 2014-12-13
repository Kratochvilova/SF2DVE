#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 13:21:52 2014

@author: pavla
"""

import re, state_parser, transition_parser, action_parser, condition_parser
from sf2dve import getDataVariable
from exceptions import invalidInputException
from copy import copy

# planarized Stateflow chart
# states - leaf states of the state hierarchy - ssid, hierarchical name, label
#       (in general format {"name":name, "en":entry actions, "du":during
#       actions, "ex":exit actions}), parents
# transitions - ssid (no longer unique), label (in general format
#       {"conditions":conditions, "ca":condition actions, "ta":transition
#       actions}), source, destination, hierarchy, orderType, order (hierarchy,
#       orderType and order together define execution order - it is determined
#       first by hierarchy number then by orderType and then by order; in all
#       cases lower number means higher priority)
# newVariables - variables declared in labels
class PlanarizedChart:
    chartID = 0
    chartName = ""
    states = {}
    transitions = []
    labelVariables = {}
    dataVariables = []

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

def parseTransitionLabel(labelString, ssid):
    labelDict = {}
    labelDict["conditions"] = ""
    labelDict["ca"] = ""
    labelDict["ta"] = []
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
        (ta, newVars) = action_parser.parse(parsedLabel[2], "trans_%s_" % ssid,
                                            newVariables)
        newVariables.update(newVars)
        labelDict["ta"].append(ta.strip())

    return (labelDict, newVariables)

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
        planarizedChart.dataVariables.append(getDataVariable(varEl))

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
    planarizedChart.states["init"] = {
        "longName":"init",
        "label":{"name":"init", "en":"", "du":"", "ex":""},
        "parents":[],
        "superstate":False
    }

    # storing transitions (ssid, label, source, destination, execution order)
    # (ssid aren't unique anymore, since there can be transition from 
    # superstate and hence several transitions with the same ssid are created)
    # transition label must also contain actions of crossed superstates
    for trans in chart.findall(".//transition"):
        labelDict = labelCache.getTransition(trans.get("SSID"))

        srcEl = trans.find('src/P[@Name="SSID"]')
        if (srcEl is None):
            src = "init"
        else:
            src = srcEl.findtext(".")
        dst = trans.findtext('dst/P[@Name="SSID"]')

        if (src == "init" and
            trans.getparent().getparent().tag != "chart" and
            (trans.find('P[@Name="labelString"]') is None or
            trans.findtext('P[@Name="labelString"]').strip() == "")):
                continue

        # for transition from superstate, one transition from each substate
        # is created; for transition to superstate, transition to the substate
        # with default transition is created or to a superstate, if there are
        # labeled default transitions
        sources = []
        if src == "init" and trans.getparent().getparent().tag == "chart":
            sources.append("init")
        elif src == "init":
            sources.append(trans.getparent().getparent().get("SSID"))
        elif (src in planarizedChart.states and 
              not planarizedChart.states[src]["superstate"]):
            sources.append(src)
        else:
            for stateSSID, state in planarizedChart.states.items():
                if (src in state["parents"] and not state["superstate"]):
                    sources.append(stateSSID)

        if dst in planarizedChart.states:
                destination = dst
        else:
            destination = findDefaultDestination(dst, chart, planarizedChart)

        # updating transition action by actions of crossed superstates
        # (sources have the same parents)
        if src != "init":
            srcParents = copy(planarizedChart.states[sources[0]]["parents"])
            dstParents = copy(planarizedChart.states[destination]["parents"])
            srcParents.reverse()
            dstParents.reverse()
            lastCommonParent = -1
            if len(srcParents) <= len(dstParents):
                minParents = len(srcParents)
            else:
                minParents = len(dstParents)
            for i in range(0, minParents):
                if srcParents[i] == dstParents[i]:
                    lastCommonParent = i
                else:
                    break
            for parentSSID in srcParents[lastCommonParent + 1:]:
                parentLabel = labelCache.getState(parentSSID)
                labelDict["ta"] = parentLabel["ex"] + labelDict["ta"]
            for parentSSID in dstParents[lastCommonParent + 1:]:
                parentLabel = labelCache.getState(parentSSID)
                labelDict["ta"] = labelDict["ta"] + parentLabel["en"]

        # determining hierarchy, orderType and order
        if sources[0] == "init":
            hierarchy = 0
            orderType = 0
        else:
            hierarchy = 1
            if src == "init":
                srcState = chart.find('.//state[@SSID="%s"]' % sources[0])
            else:
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
            planarizedChart.transitions.append({"ssid":trans.get("SSID"),
            "label":labelDict, "src":source, "dst":destination,
            "hierarchy":hierarchy, "orderType":orderType, "order":order})

    planarizedChart.labelVariables = labelCache.labelVariables

    return planarizedChart
