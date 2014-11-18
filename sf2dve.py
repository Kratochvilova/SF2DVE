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
        if (state.find('P[@Name="labelString"]') is None or
            state.findtext('P[@Name="labelString"]') == ""):
            raise invalidInputException("state without label")

def getListOfStates(states, state_names):
    if state_names == "id":
        return ", ".join(statePrefix + ssid for ssid in states.keys())
    elif state_names == "hierarchal":
        return ", ".join(statePrefix + s["longName"] for s in states.values())
    else:
        return ", ".join(statePrefix + s["label"]["name"] for s in states.values())

def sf2dve(infile, outfile, state_names):
    stateflowEtree = etree.parse(infile)
    checkInput(stateflowEtree)
    stateflow = planarization.makePlanarized(stateflowEtree)

    outfile.write("process %s%s {\n" % (processPrefix, stateflow.chartID))

    # variables
    # TODO: correct this and look for other types
    # Like this, they are local. Should they be global?
    # When corrected, if notSupportedException is raised, it shouldn't be
    # catched here
    # add newVariables from declarations in labels
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
    startTrans = False
    endTrans = False
    for trans in stateflow.transitions:
        if not startTrans:
            startTrans = True
            outfile.write("\ttrans\n")
        if endTrans:
            outfile.write(",\n\t\t")
        else:            
            endTrans = True
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
        
        conditions = []
        if trans["label"]["conditions"] != "":
            conditions.append(trans["label"]["conditions"])
        # negated conditions of transitions with higher priority
        for trans2 in stateflow.transitions:
            if (trans2["src"] == trans["src"] and 
            (trans2["hierarchy"] < trans["hierarchy"] or
            (trans2["hierarchy"] == trans["hierarchy"] and
            trans2["orderType"] < trans["orderType"]) or
            (trans2["hierarchy"] == trans["hierarchy"] and
            (trans2["orderType"] == trans["orderType"] and
            trans2["order"] < trans["order"])))):
                if trans2["label"]["conditions"] != "":
                    conditions.append("not(" + trans2["label"]["conditions"] + ")")
                else:
                    conditions.append("false")
        if conditions != []:
            outfile.write(" guard %s;" % ", ".join(conditions))

        # actions
        actions = ""
        if trans["label"]["ca"] != "":
            actions = trans["label"]["ca"]
        for action in stateflow.states[trans["src"]]["label"]["ex"]:
            actions = actions + " " + action
        if trans["label"]["ta"] != "":
            actions = actions + " " + trans["label"]["ta"]
        for action in stateflow.states[trans["dst"]]["label"]["en"]:
            actions = actions + " " + action
        if actions != "":
            if actions[-1] == ',':
                actions = actions[:-1]
            outfile.write(" effect %s;" % actions)
        
        outfile.write(" }")
        
    # during actions (transitions)
    for stateSSID, state in stateflow.states.items():
        for action in state["label"]["du"]:
            if not startTrans:
                startTrans = True
                outfile.write("\ttrans\n")
            if endTrans:
                outfile.write(",\n\t\t")
            else:            
                endTrans = True
                outfile.write("\t\t")
                
            # from -> to
            if state_names == "id":
                outfile.write("%s%s -> %s%s" % (statePrefix, stateSSID,
                                                statePrefix, stateSSID))
            elif state_names == "hierarchal":
                outfile.write("%s%s -> %s%s" % (statePrefix, 
                                                state["longName"],
                                                statePrefix, 
                                                state["longName"]))
            else:
                outfile.write("%s%s -> %s%s" % (statePrefix, 
                                                state["label"]["name"],
                                                statePrefix, 
                                                state["label"]["name"]))              

            outfile.write((" {"))
            # conditions
            conditions = []
            for trans in stateflow.transitions:
                if (trans["src"] == stateSSID):
                    if trans2["label"]["conditions"] != "":
                        conditions.append("not(" + trans["label"]["conditions"] + ")")
                    else:
                        conditions.append("false")
            if conditions != []:
                outfile.write(" guard %s;" % ", ".join(conditions))

            # actions
            actions = ""
            for action in state["label"]["du"]:
                actions = actions + " " + action
            if actions != "":
                if actions[-1] == ',':
                    actions = actions[:-1]
                outfile.write(" effect %s;" % actions)

            outfile.write(" }")

    outfile.write(";\n}\n\n")
    
    # TODO
    outfile.write("system async;\n\n")

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
