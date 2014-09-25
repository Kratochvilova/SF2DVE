#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys
from lxml import etree
import re

path = "Stateflow/machine/Children/chart/Children"
processPrefix = "process_"
statePrefix = "state_"
actionKeywords = "(entry:|during:|exit:)"
actionAbbreviations = "(en|du|ex)"

# exception for any kind of unsupported stateflow constructions
class notSupportedException(Exception): pass

class invalidInputException(Exception): pass

# plannarized stateflow
# states - leaf states of the state hierarchy - ssid, hierarchal name, label
#       parents, init (information whether there is default transition to this
#       state)
# transitions - ssid (no longer unique), label, source, destination, hierarchy,
#       order (hierarchy and order together define execution order - one
#       transition has priority over another if it has lower hierarchy number,
#       or the same hierarchy number and lower order number)
#       - for a transition from a superstate there is a transition from each
#       leaf substate
#       - for  transition to a superstate there is a transition to every leaf
#       substate, such that there is default transition to this substate and
#       all its parents with lower hierarchy then the aforementioned superstate
class plannarized:
    chartID = 0
    states = {}
    transitions = []

# TODO: create some trivial XML schema
# (there should be language setting (MATLAB or nothing) somewhere in
# ModelInformation.Model.ConfigurationSet.Array.Object.Array.Object)   
def checkInput(tree):
    # TODO: find out what to do if there is more charts or more machines
    if (len(tree.findall("Stateflow/machine")) != 1):
        raise invalidInputException("invalid number of machines")
    if (len(tree.findall("Stateflow/machine/Children/chart")) != 1):
        raise invalidInputException("invalid number of charts")
    
    # superfluous if there is validation against schema
    for state in tree.findall("//state"):
        if (state.find('P[@Name="labelString"]') == None or
            state.findtext('P[@Name="labelString"]') == ""):
            raise invalidInputException("state without label")

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

# TODO: C syntax
#       replace ';' and '\n' for ','
def parseStateLabel(label):
    if isinstance(label, etree._Element):
        labelString = label.findtext(".")
    elif isinstance(label, str):
        labelString = label
    else:
        raise TypeError()

    labelDict = {}

    if labelString == "":
        return labelDict

    # separating name
    match = re.match(r"([^\n]*)/((.|\n)*)", labelString)
    if (match != None):
        labelDict["name"] = match.group(1).strip()
        labelString = match.group(2)
    else:
        match = re.match(r"([^\n]*)\n((.|\n)*)", labelString)
        if (match != None):
            labelDict["name"] = match.group(1).strip()
            labelString = match.group(2)
        else:
            labelDict["name"] = labelString
            return labelDict
    
    # puting "entry:" before possible entry actions directly after '/' or '\n'
    # character after the state name    
    if re.match(actionKeywords, labelString) == None:
        labelString = "entry:" + labelString
    
    # replacing abreviations
    labelString = labelString.replace("en:", "entry:")
    labelString = labelString.replace("du:", "during:")
    labelString = labelString.replace("ex:", "exit:")

    # determining intervals of actions of one type
    limits = [m.start() for m in re.finditer(actionKeywords, labelString)]
    limits.sort()
    limits.append(-1)
    intervals = []
    temp = None
    for limit in limits:
        if (temp != None):
            intervals.append((temp, limit))
        temp = limit

    # dividing label
    labelDict["en"] = []
    labelDict["du"] = []
    labelDict["ex"] = []
    
    for interval in intervals:
        if labelString[interval[0]:].startswith("entry:"):
            if (interval[1] == -1):
                labelDict["en"].append(labelString[interval[0]+len("entry:"):])
            else:
                labelDict["en"].append(labelString[interval[0]+len("entry:"):interval[1]])
        elif labelString[interval[0]:].startswith("during:"):
            if (interval[1] == -1):
                labelDict["du"].append(labelString[interval[0]+len("during:"):])
            else:
                labelDict["du"].append(labelString[interval[0]+len("during:"):interval[1]])
        elif labelString[interval[0]:].startswith("exit:"):
            if (interval[1] == -1):
                labelDict["ex"].append(labelString[interval[0]+len("exit:"):])
            else:
                labelDict["ex"].append(labelString[interval[0]+len("exit:"):interval[1]])

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
            label = ""
        else:
            label = labelEl.findtext(".")
            if label == None:
                label = ""
        listOfPaths += getDefaultPaths(stateEl.find('Children/state[@SSID="%s"]' % dst), 
                                       listOfLabels + [label])
    return listOfPaths

def makePlannarized(tree):
    stateflow = plannarized()

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
            label = ""
        else:
            label = labelEl.findtext(".")

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
            destinations = [(dst, label)]
        else:
            parent = tree.find('//state[@SSID="%s"]' % dst)
            destinations = getDefaultPaths(parent, [label])

        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for source in sources:
            for (destination, pathLabel) in destinations:
                stateflow.transitions.append({"ssid":trans.get("SSID"),
                "label":pathLabel, "src":source, "dst":destination,
                "hierarchy":hierarchy, "order":order})

    return stateflow

def getListOfStates(states, state_names):
    if state_names == "id":
        return ", ".join(statePrefix + ssid for ssid in states.keys())
    elif state_names == "hierarchal":
        return ", ".join(statePrefix + s["longName"] for s in states.values())
    else:
        return ", ".join(statePrefix + s["label"]["name"] for s in states.values())

def writeStateActions(labelDict, actionType, outfile):
    if actionType != "en" and actionType != "du" and actionType != "ex":
        raise ValueError('actionType should be either "en", "du" or "ex"')
    
    if actionType not in labelDict.keys():
        return
    for action in labelDict[actionType]:
        outfile.write(" effect %s" % action)
        if (action[-1] != ";"):
            outfile.write(";")

# TODO: actions don't have to be in curly brackets - correct this
def writeTransitionActions(label, actionType, outfile):
    if (label == ""):
        return
    
    if (isinstance(label, list)):
        for l in label:
            writeTransitionActions(l, actionType, outfile)
        return

    if (len(label.split("/")) == 1 and actionType == "action"):
        return

    if actionType == "condition":
        part = 0
    elif actionType == "action":
        part = 1
    
    for action in re.findall("{(.*)}", label.split("/")[part]):
        action = action.strip()
        if (action != ""):
            outfile.write(" effect %s" % action)
            if (action[-1] != ";"):
                outfile.write(";")

def repareCondition(condition):
    if (condition == ""):
        return "true"
    else:
        return condition

def writeTransitionConditions(label, outfile, positive):
    if (label == ""):
        # TODO: if positive is false, there shoud be raised exception or
        # returned something that would indicate, what's happend (this means
        # that there is transition that cannot be taken)
        return

    if (isinstance(label, list)):
        for l in label:
            writeTransitionConditions(l, outfile, positive)
        return

    conditions = " and ".join(repareCondition(condition.strip()) for condition
        in re.findall("\[(.*)\]", label.split("/")[0]))

    if (conditions != ""):
        if (positive):
            outfile.write(" guard %s" % conditions)
        else:
            outfile.write(" guard not(%s)" % conditions)
        if (conditions[-1] != ';'):
            outfile.write(';')

def sf2dve(infile, outfile, disable_validation, state_names):
    tree = etree.parse(infile)

    if not disable_validation:
        checkInput(tree)

    stateflow = makePlannarized(tree)

    # TODO: check syntax; check if stateflow is allways synchronous or
    #       something like that and if not, try to resolve this
    outfile.write("system sync;\n\n")

    # TODO: properties
    outfile.write("property true\n\n")

    outfile.write("process %s%s {\n" % (processPrefix, stateflow.chartID))

    # variables
    # TODO: correct this and look for other types
    # Like this, they are local. Should they be global?
    # When corrected, if notSupportedException is raised, it shouldn't be
    # catched here
    for var in tree.findall("%s/data" % path):
        try:
            varType = var.findtext('P[@Name="dataType"]')
            if (varType.startswith("uint")):
                outfile.write("\tint %s;\n" % var.get("name"))
            if (varType == "boolean"):
                outfile.write("\tbyte %s;\n" % var.get("name"))
            else:
                raise notSupportedException("Variable of unsupported type.")
        except notSupportedException as e:
            print(e, file=sys.stderr)

    # states
    outfile.write("\tstate %s;\n" % getListOfStates(stateflow.states, 
                                                    state_names))

    # initial state
    outfile.write("\tinit %sinit;\n" % statePrefix)

    # transitions (without loops representing during actions)
    # TODO: can there be a "guard" string before every guard and "effect"
    #       string before every effect or is it necessary to have only one?
    #       Can there be ';' after the last guards and effects?
    #       Can there be ',' after the last transition?
    outfile.write("\ttrans\n")
    for trans in stateflow.transitions:
        outfile.write("\t\t")

        # from -> to
        if state_names == "id":
            outfile.write("%s%s -> %s%s" % (statePrefix, trans["src"],
                                            statePrefix, trans["dst"]))
        elif state_names == "hierarchal":
            outfile.write("%s%s -> %s%s" % (statePrefix,
                          stateflow.states[trans["src"]]["longName"],
                          statePrefix,
                          stateflow.states[trans["dst"]]["longName"]))
        else:
            outfile.write("%s%s -> %s%s" % (statePrefix,
                          stateflow.states[trans["src"]]["label"]["name"],
                          statePrefix,
                          stateflow.states[trans["dst"]]["label"]["name"]))

        outfile.write((" {"))
        # conditions, TODO: condition actions should perhaps take place even
        #                   if condition is false - need to find out!
        writeTransitionConditions(trans["label"], outfile, True)
        try:
            if isinstance(trans["label"], list):
                pass
            elif (re.search("{(.*)}", trans["label"].split("/")[0]) != None):
                raise notSupportedException("Condition action on transition "
                "detected. They are not supported (yet), so this may cause "
                "wrong behaviour. They will be considered as normal actions "
                "and will take place before exit action of source state (only "
                "when transition is taken).")
        except notSupportedException as e:
            print(e)

        # negated conditions of transitions with higher priority - this should
        # solve priorities in case of conflicting transitions
        # (transition A is of higher priority then transition B if A has lower
        # order or if orders are the same and A is higher in hierarchy)
        # TODO: comparing strings (trans2["order"] < trans["order"])?
        for trans2 in stateflow.transitions:
            if (trans2["src"] == trans["src"] and
                (trans2["order"] < trans["order"] or
                (trans2["order"] == trans["order"] and
                trans2["hierarchy"] > trans["hierarchy"]))):
                writeTransitionConditions(trans2["label"], outfile, False)

        # actions
        writeTransitionActions(trans["label"], "condition", outfile)

        if (trans["src"] in stateflow.states.keys()):
            writeStateActions(stateflow.states[trans["src"]]["label"],
                              "ex", outfile)

        writeTransitionActions(trans["label"], "action", outfile)

        if (trans["dst"] in stateflow.states.keys()):
            writeStateActions(stateflow.states[trans["dst"]]["label"],
                              "ex", outfile)

        outfile.write(" }")
        outfile.write(",\n")

    # during actions (transitions)
    for stateSSID, state in stateflow.states.items():
        if "du" not in state["label"].keys():
            continue
        for action in state["label"]["du"]:
            outfile.write("\t\t")

            # from -> to
            if state_names == "id":
                outfile.write("%s%s -> %s%s" % (statePrefix, stateSSID,
                                                statePrefix, stateSSID))
            elif state_names == "hierarchal":
                outfile.write("%s%s -> %s%s" % (statePrefix, state["longName"],
                                                statePrefix, state["longName"]))
            else:
                outfile.write("%s%s -> %s%s" % (statePrefix, state["label"]["name"],
                                                statePrefix, state["label"]["name"]))              

            outfile.write((" {"))
            # conditions
            for trans in stateflow.transitions:
                if (trans["src"] == stateSSID):
                    writeTransitionConditions(trans["label"], outfile, False)

            # actions
            writeStateActions(state["label"], "du", outfile)

            outfile.write(" }")
            outfile.write(",\n")

    outfile.write("}\n")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input Stateflow XML file",
                        type=argparse.FileType('r'))
    parser.add_argument("output", help="output DVE file",
                        type=argparse.FileType('w'))
    parser.add_argument("-d", "--disable-validation", help="partially " +\
                        "disables input validation", action="store_true",)
    parser.add_argument("-s", "--state-names", help="as name of state " +\
                        "will be used: id (unique but not human friendly), " +\
                        "hierarchal name (longer, may not be unique) or " +\
                        "original name (shorter, may not be unique). Use " +\
                        "id (default) when generating input for DiVinE.",
                        choices=["id", "hierarchal", "name"], default="id")
    args = parser.parse_args()
    
    try:
        sf2dve(args.input, args.output, args.disable_validation, args.state_names)
    except invalidInputException as e:
        print("Input is not valid stateflow: %s" % e, file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
