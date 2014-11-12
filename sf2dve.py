#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys, re, planarization
from lxml import etree

path = "Stateflow/machine/Children/chart/Children"
processPrefix = "process_"
statePrefix = "state_"

# exception for any kind of unsupported stateflow constructions
class notSupportedException(Exception): pass

class invalidInputException(Exception): pass

# TODO: create some trivial XML schema
# (there should be language setting (MATLAB or nothing) somewhere in
# ModelInformation.Model.ConfigurationSet.Array.Object.Array.Object)   
def checkInput(stateflowEtree):
    # TODO: find out what to do if there is more charts or more machines
    if (len(stateflowEtree.findall("Stateflow/machine")) != 1):
        raise invalidInputException("invalid number of machines")
    if (len(stateflowEtree.findall("Stateflow/machine/Children/chart")) != 1):
        raise invalidInputException("invalid number of charts")
    
    # superfluous if there is validation against schema
    for state in stateflowEtree.findall("//state"):
        if (state.find('P[@Name="labelString"]') == None or
            state.findtext('P[@Name="labelString"]') == ""):
            raise invalidInputException("state without label")

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
def writeTransitionActions(labelDict, actionType, outfile):
    if actionType not in labelDict.keys():
        return

    outfile.write(" effect %s" % labelDict[actionType])
    if (labelDict[actionType][-1] != ";"):
        outfile.write(";")

def repareCondition(condition):
    if (condition == ""):
        return "true"
    else:
        return condition

def writeTransitionConditions(labelDict, outfile, positive):
    if "conditions" not in labelDict.keys():
        # TODO: if positive is false, there shoud be raised exception or
        # returned something that would indicate, what has happend (this means
        # that there is transition that cannot be taken)
        return

    if (positive):
        outfile.write(" guard %s" % labelDict["conditions"])
    else:
        outfile.write(" guard not(%s)" % labelDict["conditions"])
    if (labelDict["conditions"][-1] != ';'):
        outfile.write(';')

def sf2dve(infile, outfile, state_names):
    stateflowEtree = etree.parse(infile)
    checkInput(stateflowEtree)
    stateflow = planarization.makePlanarized(stateflowEtree)

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
    for var in stateflowEtree.findall("%s/data" % path):
        try:
            varType = var.findtext('P[@Name="dataType"]')
            if (varType.startswith("uint")):
                outfile.write("\tint %s;\n" % var.get("name"))
            if (varType == "boolean"):
                outfile.write("\tbyte %s;\n" % var.get("name"))
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
    if stateflow.transitions != []:
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
        writeTransitionConditions(trans["label"][0], outfile, True)

        # negated conditions of transitions with higher priority - this should
        # solve priorities in case of conflicting transitions
        # TODO: comparing strings (trans2["order"] < trans["order"])?
        for trans2 in stateflow.transitions:
            if (trans2["src"] == trans["src"] and 
            (trans2["hierarchy"] < trans["hierarchy"] or
            (trans2["hierarchy"] == trans["hierarchy"] and
            trans2["orderType"] < trans["orderType"]) or
            (trans2["hierarchy"] == trans["hierarchy"] and
            (trans2["orderType"] == trans["orderType"] and
            trans2["order"] < trans["order"])))):
                writeTransitionConditions(trans2["label"][0], outfile, False)

        # actions
        writeTransitionActions(trans["label"][0], "condition", outfile)

        if (trans["src"] in stateflow.states.keys()):
            writeStateActions(stateflow.states[trans["src"]]["label"],
                              "ex", outfile)
            
        writeTransitionActions(trans["label"][0], "action", outfile)

        if (trans["dst"] in stateflow.states.keys()):
            writeStateActions(stateflow.states[trans["dst"]]["label"],
                              "en", outfile)
        
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
                    writeTransitionConditions(trans["label"][0], outfile, False)

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
    parser.add_argument("-s", "--state-names", help="as name of state " +\
                        "will be used: id (unique but not human friendly), " +\
                        "hierarchal name (longer, may not be unique) or " +\
                        "original name (shorter, may not be unique). Use " +\
                        "id (default) when generating input for DiVinE.",
                        choices=["id", "hierarchal", "name"], default="id")
    args = parser.parse_args()
    
    try:
        sf2dve(args.input, args.output, args.state_names)
    except invalidInputException as e:
        print("Input is not valid stateflow: %s" % e, file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
