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
Created on Thu Sep 25 13:21:52 2014

@author: pavla
"""

import re, state_parser, transition_parser, action_parser, condition_parser
from copy import copy
from extendedExceptions import notSupportedException

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

def appendSemicolon(string):
    if string.strip()[-1] == ';':
        return string
    return string + ';'

def getStateName(labelString):
    match = re.match(r"([^\n]*?)/", labelString)
    if match is not None:
        return match.group(1)
    match = re.match(r"([^\n]*)\n", labelString)
    if match is not None:
        return match.group(1)
    return labelString

def parseStateLabel(labelString, ssid):
    labelDict = {}

    # separating name and fixing rest of the label (puting "en:" on the
    # begining if there is no action keyword)
    labelDict["name"] = getStateName(labelString)
    labelString = labelString[len(labelDict["name"])+1:].strip()
    labelDict["name"] = labelDict["name"].strip()
    if labelString != "" and re.match(r"(entry|en|during|du|exit|ex|bind|on)",
                                      labelString) is None:
        labelString = "en:" + labelString

    action_keywords = {"entry":"en", "during":"du", "exit":"ex"}

    # dividing label
    labelDict["en"] = []
    labelDict["du"] = []
    labelDict["ex"] = []
    labelVariables = {}

    parsedLabel = state_parser.parse(labelString)
    if parsedLabel is None:
        return (labelDict, labelVariables)
    for (keywordPart, actionPart) in parsedLabel:
        if "bind" in keywordPart:
            raise notSupportedException('"bind" actions')
        if "on" in keywordPart:
            raise notSupportedException('"on event" actions')
        actionPart = appendSemicolon(actionPart)
        (parsedActionPart, newVars) = action_parser.parse(actionPart,
                                                          "state_%s_" % ssid,
                                                          labelVariables)
        labelVariables.update(newVars)
        for (keyword, abbreviation) in action_keywords.items():
            if keyword in keywordPart or abbreviation in keywordPart:
                labelDict[abbreviation] += parsedActionPart

    return (labelDict, labelVariables)

def parseTransitionLabel(labelString, ssid):
    labelDict = {}
    labelDict["condition"] = ""
    labelDict["ca"] = []
    labelDict["ta"] = []
    labelVariables = {}

    parsedLabel = transition_parser.parse(labelString.strip())
    if parsedLabel[0] is not None:
        raise notSupportedException("events in transition labels")
    if parsedLabel[1] is not None:
        labelDict["condition"] = condition_parser.parse(parsedLabel[1]).strip()
    if parsedLabel[2] is not None:
        parsedLabel[2] = appendSemicolon(parsedLabel[2])
        (labelDict["ca"], newVars) = action_parser.parse(parsedLabel[2],
                                                         "trans_%s_" % ssid,
                                                         labelVariables)
        labelVariables.update(newVars)
    if parsedLabel[3] is not None:
        parsedLabel[3] = appendSemicolon(parsedLabel[3])
        (labelDict["ta"], newVars) = action_parser.parse(parsedLabel[3],
                                                         "trans_%s_" % ssid,
                                                         labelVariables)
        labelVariables.update(newVars)

    return (labelDict, labelVariables)

# planarized Stateflow chart
# states 
#   - leaf states of the state hierarchy
#   - ssid = {hierarchical name, label, parents}
#       - label = {name, entry actions, during actions, exit actions}
# transitions
#   - {ssid, label, source, destination, srcHierarchy, transType, order}
#       - ssid is no longer unique
#       - label = {condition, condition actions, transition actions}
#       - scrHierarchy, transType and order together define execution order
#         (determined first by srcHierarchy, then by transType and then by
#         order; in all cases lower number means higher priority)
# variables
#   - name = {variable type, constant, initialization, scope}
class PlanarizedChart:
    chartID = 0
    chartName = ""
    states = {}
    transitions = []
    variables = {}

    def addState(self, stateEl, labelCache):
        stateSSID = stateEl.get("SSID")
        stateLabel = labelCache.getState(stateSSID)

        parents = []
        longName = stateLabel["name"]
        parent = stateEl.getparent().getparent()
        while parent.tag == "state":
            parents.append(parent.get("SSID"))
            parentLabel = labelCache.getState(parent.get("SSID"))
            longName = parentLabel["name"] + "_" + longName
            stateLabel["du"] = parentLabel["du"] + stateLabel["du"]
            parent = parent.getparent().getparent()

        self.states[stateSSID] = {
            "longName":longName,
            "label":stateLabel,
            "parents":parents
        }

    def addVariable(self, varEl):
        typeConversions = {"int":["int16", "int32", "uint8", "uint16",
                                  "uint32", "int"],
                           "byte":["int8", "boolean"]}
        varDef = {}

        varType = varEl.findtext('P[@Name="dataType"]')
        if varType in typeConversions["int"]:
            varDef["type"] = "int"
        elif varType in typeConversions["byte"]:
            varDef["type"] = "byte"
        else:
            raise notSupportedException("variables of type %s" % varType)

        varScope = varEl.findtext('P[@Name="scope"]')
        varDef["const"] = False
        if varScope == "LOCAL_DATA" or varScope == "OUTPUT_DATA":
            varDef["scope"] = "local"
        elif varScope == "INPUT_DATA":
            varDef["scope"] = "input"
        elif varScope == "CONSTANT":
            varDef["scope"] = "local"
            varDef["const"] = True
        else:
            raise notSupportedException("variables of scope %s" % varScope)

        initialValueEl = varEl.find('props/P[@Name="initialValue"]')
        if initialValueEl is None:
            varDef["init"] = None
        else:
            varDef["init"] = initialValueEl.findtext(".")

        self.variables[varEl.get("name")] = varDef

def negateConditions(conditions):
    if conditions == []:
        return "false"

    negatedConditions = []
    for cond in conditions:
        if cond == "":
            negatedConditions.append("false")
        else:
            negatedConditions.append("not (%s)" % cond)
    return " or ".join(negatedConditions)

def findSrcPaths(currentPath, paths, labelCache, chart):
    if currentPath[0].find("Children") is None:
        return paths + [currentPath]

    children = currentPath[0].findall("Children/state")
    for child in children:
        newActions = labelCache.getState(child.get("SSID"))["ex"] + currentPath[1]
        paths = findSrcPaths((child, newActions), paths, labelCache, chart)

    return paths

def findDstPaths(currentPath, paths, labelCache, chart):
    if currentPath[0].find("Children") is None:
        return paths + [currentPath]

    defTrans = sorted(filter(lambda x:x.find('src/P[@Name="SSID"]') is None,
                             currentPath[0].findall('Children/transition')),
                      key=lambda transEl:transEl.findtext('P[@Name="executionOrder"]'))

    negatedConditions = []

    for transEl in defTrans:
        dstSSID = transEl.findtext('dst/P[@Name="SSID"]')
        dstEl = currentPath[0].find('Children/state[@SSID="%s"]' % dstSSID)
        transLabel = labelCache.getTransition(transEl.get("SSID"))

        newConditions = currentPath[1] + negatedConditions
        if transLabel["condition"] != "":
            newConditions.append(transLabel["condition"])
        negatedConditions.append(negateConditions([transLabel["condition"]]))
        newActions = currentPath[2] + transLabel["ca"] + transLabel["ta"] + labelCache.getState(dstSSID)["en"]

        paths = findDstPaths((dstEl, newConditions, newActions), 
                                 paths, labelCache, chart)

    paths.append(("error", currentPath[1] + negatedConditions, currentPath[2]))

    return paths

def makePlanarized(chart):
    planarizedChart = PlanarizedChart()
    labelCache = LabelCache(chart)

    planarizedChart.chartID = chart.get("id")
    planarizedChart.chartName = chart.findtext('P[@Name="name"]')

    # storing states
    for stateEl in chart.findall(".//state"):
        if stateEl.find("Children") is None:
            planarizedChart.addState(stateEl, labelCache)
    planarizedChart.states["start"] = {
        "longName":"start",
        "label":{"name":"start", "en":[], "du":[], "ex":[]},
        "parents":[]
    }
    planarizedChart.states["error"] = {
        "longName":"error",
        "label":{"name":"error", "en":[], "du":[], "ex":[]},
        "parents":[]
    }

    # storing transitions
    for trans in chart.findall(".//transition"):
        transLabel = labelCache.getTransition(trans.get("SSID"))
        transParent = trans.getparent().getparent()
        transParentSSID = transParent.get("SSID")

        srcEl = trans.find('src/P[@Name="SSID"]')
        if srcEl is None:
            srcSSID = "start"
        else:
            srcSSID = srcEl.findtext(".")
        dstSSID = trans.findtext('dst/P[@Name="SSID"]')

        # default transitions are ignored (except the initial one)
        if srcSSID == "start" and transParent.tag != "chart":
            continue

        # updating transition actions with actions of crossed superstates,
        # source and destination
        # updating condition actions with during actions of superstates of the
        # source state
        if srcSSID != "start":
            srcLabel = labelCache.getState(srcSSID)
            if srcSSID == transParentSSID:
                duActions = copy(srcLabel["du"])
                exActions = []
                exiting = False
            else:
                duActions = []
                exActions = copy(srcLabel["ex"])
                exiting = True
            src = chart.find('.//state[@SSID="%s"]' % srcSSID)
            srcParent = src.getparent().getparent()
            while srcParent.tag == "state":
                if srcParent.get("SSID") == transParentSSID:
                    exiting = False
                parentLabel = labelCache.getState(srcParent.get("SSID"))
                duActions = parentLabel["du"] + duActions
                if exiting:
                    exActions = exActions + parentLabel["ex"]
                srcParent = srcParent.getparent().getparent()
            transLabel["ca"] = duActions + transLabel["ca"]
            transLabel["ta"] = exActions + transLabel["ta"]

        if dstSSID == transParentSSID:
            enActions = []
        else:
            enActions = copy(labelCache.getState(dstSSID)["en"])
        dst = chart.find('.//state[@SSID="%s"]' % dstSSID)
        dstParent = dst.getparent().getparent()
        while dstParent.tag == "state" and dstParent.get("SSID") != transParentSSID:
            enActions = labelCache.getState(dstParent.get("SSID"))["en"] + enActions
            dstParent = dstParent.getparent().getparent()
        transLabel["ta"] = transLabel["ta"] + enActions

        # for transition from a superstate, one transition from each substate
        # is created;
        if srcSSID == "start" and transParent.tag == "chart":
            srcPaths = [("start", [])]
        else:
            srcEl = chart.find('.//state[@SSID="%s"]' % srcSSID)
            srcPaths = findSrcPaths((srcEl, []), [], labelCache, chart)

        # for transition to a superstate, one transition to each substate with
        # default transition is created (and to an error state, if there
        # are labeled default transitions)
        dstEl = chart.find('.//state[@SSID="%s"]' % dstSSID)
        if transLabel["condition"] == "":
            conditions = []
        else:
            conditions = [transLabel["condition"]]
        dstPaths = findDstPaths((dstEl, conditions, []), 
                                [], labelCache, chart)

        # determining source hierarchy, transition type and order
        if srcSSID == "start":
            srcHierarchy = 0
        else:
            srcHierarchy = 1
            src = chart.find('.//state[@SSID="%s"]' % srcSSID)
            srcParent = src.getparent().getparent()
            while srcParent.tag != "chart":
                srcHierarchy += 1
                srcParent = srcParent.getparent().getparent()

        if srcSSID == "start":
            transType = 0
        elif transParent.get("SSID") == srcSSID:
            transType = 2
        else:
            transType = 1

        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for srcPath in srcPaths:
            for dstPath in dstPaths:
                if isinstance(srcPath[0], str):
                    srcSSID = "start"
                else:
                    srcSSID = srcPath[0].get("SSID")
                if isinstance(dstPath[0], str):
                    dstSSID = "error"
                else:
                    dstSSID = dstPath[0].get("SSID")

                planarizedChart.transitions.append({"ssid":trans.get("SSID"),
                "src":srcSSID, "dst":dstSSID, "conditions":dstPath[1],
                "actions": transLabel["ca"] + srcPath[1] + transLabel["ta"] + dstPath[2],
                "srcHierarchy":srcHierarchy, "transType":transType,
                "order":order})

    # storing transition from state "start" to state "error"
    planarizedChart.transitions.append({"ssid":"start", "src":"start",
    "dst":"error", "conditions":[], "actions": [], "srcHierarchy":1,
    "transType":0, "order":0})

    # storing variables
    for varEl in chart.findall(".//data"):
        planarizedChart.addVariable(varEl)
    planarizedChart.variables.update(labelCache.labelVariables)

    return planarizedChart
