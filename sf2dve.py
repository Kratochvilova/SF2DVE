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

# exception for any kind of unsupported stateflow constructions
class notSupportedException(Exception): pass

class invalidInputException(Exception): pass

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
    if (label == None or label == ""):
        return "entry: during: exit: "

    # deleting name and puting "entry:" before possible entry actions after '/'
    match = re.match(r"[^\n]*/((.|\n)*)", label)
    if (match != None):
        label = "entry:" + match.group(1)
    else:
        match = re.match(r"[^\n]*\n((.|\n)*)", label)
        if (match != None):
            label = match.group(1)
        else:
            return "entry: during: exit: "

    # replacing abreviations
    label = label.replace("en:", "entry:")
    label = label.replace("du:", "during:")
    label = label.replace("ex:", "exit:")

    # determining intervals of actions of one type
    limits = [m.start() for m in re.finditer(actionKeywords, label)]
    limits.sort()
    limits.append(-1)
    intervals = []
    temp = None
    for limit in limits:
        if (temp != None):
            intervals.append((temp, limit))
        temp = limit

    # dividing label
    entryActions = ""
    duringActions = ""
    exitActions = ""

    for interval in intervals:
        if label[interval[0]:].startswith("entry:"):
            if (interval[1] == -1):
                entryActions += label[interval[0]+len("entry:"):]
            else:
                entryActions += label[interval[0]+len("entry:"):interval[1]]
        elif label[interval[0]:].startswith("during:"):
            if (interval[1] == -1):
                duringActions += label[interval[0]+len("during:"):]
            else:
                duringActions += label[interval[0]+len("during:"):interval[1]]
        elif label[interval[0]:].startswith("exit:"):
            if (interval[1] == -1):
                exitActions += label[interval[0]+len("exit:"):]
            else:
                exitActions += label[interval[0]+len("exit:"):interval[1]]

    return ("entry: " + entryActions.strip() +
            "during: " + duringActions.strip() +
            "exit: " + exitActions.strip())

def makePlannarized(tree):
    stateflow = plannarized()

    # TODO: find out what is chart and machine (if any of them correspond with
    #       process in DVE and what to do it there are more of them)
    stateflow.chartID = tree.find("Stateflow/machine/Children/chart").get("id")        

    # storing leaf states of the state hierarchy (ssid, name, label, parents)
    # "init" is for future information whether there is some default transition
    for state in tree.findall("//state"):
        if (state.find("Children") == None):
            labelElement = state.find('P[@Name="labelString"]')
            label = parseStateLabel(labelElement.findtext("."))

            parents = []
            name = getStateName(labelElement)
            longName = name
            parent = state.getparent().getparent()
            while (parent.tag == "state"):
                parents.append(parent.get("SSID"))
                longName = getStateName(parent.find('P[@Name="labelString"]'))\
                       + "." + longName
                parent = parent.getparent().getparent()

            stateflow.states[state.get("SSID")] = {"longName":longName,
            "name":name, "label":label, "parents":parents, "init":False}

    # seting "init"
    for trans in tree.findall("//transition"):
        srcElement = trans.find('src/P[@Name="SSID"]')
        dst = trans.findtext('dst/P[@Name="SSID"]')
        if (srcElement == None and dst in stateflow.states.keys()):
            stateflow.states[dst]["init"] = True

    stateflow.states["init"] = {"longName":"init", "name":"init",
    "label":"entry: during: exit: ", "parents":[], "init":True}

    # storing transitions (ssid, label, source, destination, execution order)
    # (ssid aren't unique anymore since there can be transition from superstate
    # and hence several transitions with the same ssid are created)
    for trans in tree.findall("//transition"):
        labelElement = trans.find('P[@Name="labelString"]')
        if (labelElement == None):
            label = ""
        else:
            label = labelElement.findtext(".")

        srcElement = trans.find('src/P[@Name="SSID"]')
        if (srcElement == None):
            src = "init"
        else:
            src = srcElement.findtext(".")
        dstElement = trans.find('dst/P[@Name="SSID"]')
        dst = dstElement.findtext(".")

        if (src == "init" and trans.getparent().getparent().tag != "chart"):
            continue

        # if there is transition from some superstate, one transition from
        # each substate is created
        # if there is transition to some superstate, transition to the substate
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
            destination = dst
        else:
            child = tree.find('//state[@SSID="%s"]' % dst)
            while (child.find("Children") != None):
                # TODO: this would be better, but for some reason these xpath
                # conditions won't work:
                # childTrans = child.find('Children/transition/src[not(P)]')
                for t in child.findall("Children/transition"):
                    if (t.find('src/P[@Name="SSID"]') == None):
                        childTrans = t
                        break
                childSSID = childTrans.findtext('dst/P[@Name="SSID"]')
                child = child.find('Children/state[@SSID="%s"]' % childSSID)
            destination = childSSID

        order = int(trans.findtext('P[@Name="executionOrder"]'))

        for source in sources:
            stateflow.transitions.append({"ssid":trans.get("SSID"),
            "label":label, "src":source, "dst":destination,
            "hierarchy":hierarchy, "order":order})

    return stateflow

def writeStateActions(label, actionType, outfile):
    if (label == None or label == ""):
        return

    if actionType == "entry:":
        nextType = "during:"
    elif actionType == "during:":
        nextType = "exit:"
    elif actionType == "exit:":
        nextType = ""
    else:
        return

    match = re.search(actionType + r"((.|\n)*)" + nextType, label)
    if (match == None):
        return
    action = match.group(1).strip()
    if (action != ""):
        outfile.write(" effect %s" % action)
        if (action[-1] != ";"):
            outfile.write(";")

# TODO: actions probably don't have to be in curly brackets - correct this
def writeTransitionActions(label, actionType, outfile):
    if (label == ""):
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

# TODO: conditions probably don't have to be in brackets - correct this
def writeTransitionConditions(label, outfile, positive):
    if (label == ""):
        # TODO: if positive is false, there shoud be raised exception or
        # returned something that would indicate, what's happend (this means
        # that there is transition that cannot be taken)
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
    outfile.write("\tstate ")
    if state_names == "id":
        outfile.write(", ".join(statePrefix + ssid for ssid
                                in stateflow.states.keys()))
    elif state_names == "hierarchal":
        outfile.write(", ".join(statePrefix + state["longName"] for ssid, state 
                                in stateflow.states.items()))
    else:
        outfile.write(", ".join(statePrefix + state["name"] for ssid, state
                                in stateflow.states.items()))
    outfile.write(";\n")

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
                          stateflow.states[trans["src"]]["name"],
                          statePrefix,
                          stateflow.states[trans["dst"]]["name"]))

        outfile.write((" {"))
        # conditions, TODO: condition actions should perhaps take place even
        #                   if condition is false - need to find out!
        writeTransitionConditions(trans["label"], outfile, True)
        try:
            if (re.search("{(.*)}", trans["label"].split("/")[0]) != None):
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
                              "exit:", outfile)

        writeTransitionActions(trans["label"], "action", outfile)

        if (trans["dst"] in stateflow.states.keys()):
            writeStateActions(stateflow.states[trans["dst"]]["label"],
                              "exit:", outfile)

        outfile.write(" }")
        outfile.write(",\n")

    # during actions (transitions)
    for stateSSID, state in stateflow.states.items():
        if (re.search(r"during:((.|\n)*)exit:",
                      state["label"]).group(1).strip() != ""):
            outfile.write("\t\t")

            # from -> to
            if state_names == "id":
                outfile.write("%s%s -> %s%s" % (statePrefix, stateSSID,
                                                statePrefix, stateSSID))
            elif state_names == "hierarchal":
                outfile.write("%s%s -> %s%s" % (statePrefix, state["longName"],
                                                statePrefix, state["longName"]))
            else:
                outfile.write("%s%s -> %s%s" % (statePrefix, state["name"],
                                                statePrefix, state["name"]))              

            outfile.write((" {"))
            # conditions
            for trans in stateflow.transitions:
                if (trans["src"] == stateSSID):
                    writeTransitionConditions(trans["label"], outfile, False)

            # actions
            writeStateActions(state["label"], "during:", outfile)

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
                        "hierarchal name (should be unique but may be " +\
                        "long) or original name (short but may not be " +\
                        "unique - do not use as input for DiVinE)",
                        choices=["id", "hierarchal", "name"], default="id")
    args = parser.parse_args()
    
    try:
        sf2dve(args.input, args.output, args.disable_validation, args.state_names)
    except invalidInputException as e:
        print("Input is not valid stateflow: %s" % e, file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
