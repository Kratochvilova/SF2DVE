#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys, re, planarization
from lxml import etree
from exceptions import notSupportedException, invalidInputException

processPrefix = "process_"
statePrefix = "state_"

# TODO: create some trivial XML schema
# (there should be language setting (MATLAB or nothing) somewhere in
# ModelInformation.Model.ConfigurationSet.Array.Object.Array.Object)   
def checkInput(stateflowEtree):
    # TODO: find out what to do if there is more charts or more machines
    if (len(stateflowEtree.findall("Stateflow/machine")) != 1):
        raise invalidInputException("invalid number of machines")
    
    # superfluous if there is validation against schema
    for state in stateflowEtree.findall("//state"):
        if (state.find('P[@Name="labelString"]') is None or
            state.findtext('P[@Name="labelString"]') == ""):
            raise invalidInputException("state without label")

def getListOfStates(states, state_names):
    if state_names == "id":
        return ", ".join(statePrefix + ssid for ssid in states.keys())
    elif state_names == "hierarchical":
        return ", ".join(statePrefix + s["longName"] for s in states.values())
    else:
        return ", ".join(statePrefix + s["label"]["name"] for s in states.values())

def getDataVariable(varEl):
    typeConversions = {"int":["int16", "int32", "uint8", "uint16", "uint32", 
                              "int"],
                       "byte":["int8", "boolean"]}
                       
    varScope = varEl.findtext('P[@Name="scope"]')
    if varScope == "LOCAL_DATA" or varScope == "OUTPUT_DATA":
        var = ""
    elif varScope == "CONSTANT":
        var = "const "
    elif varScope == "INPUT_DATA":
        var = "input "
    else:
        raise notSupportedException("Variable of unsupported scope: %s %s" 
                                    % (varScope, varEl.get("name")))
    
    varType = varEl.findtext('P[@Name="dataType"]')
    if varType in typeConversions["int"]:
        var += "int "
    elif varType in typeConversions["byte"]:
        var += "byte "
    else:
        raise notSupportedException("Variable of unsupported type: %s %s" 
                                    % (varType, varEl.get("name")))
    
    var += varEl.get("name")
        
    initialValueEl = varEl.find('props/P[@Name="initialValue"]')
    if initialValueEl != None:
        var += " = " + initialValueEl.findtext(".")
    
    return var

def writeProcess(chart, outfile, state_names):
    # process declaration    
    if state_names == "id":
        outfile.write("process %s%s {\n" % (processPrefix, chart.chartID))
    else:
        outfile.write("process %s%s {\n" % (processPrefix, chart.chartName))

    # variables    
    for variable in chart.dataVariables:
        outfile.write("\t%s;\n" % variable)
        
    for varName, varType in chart.labelVariables.items():
        outfile.write("\t%s%s;\n" % (varType, varName))
    
    # states
    outfile.write("\tstate %s;\n" % getListOfStates(chart.states,
                                                    state_names))
    outfile.write("\tinit %sinit;\n" % statePrefix)

    # transitions (without loops representing during actions)
    startTrans = False
    for trans in chart.transitions:
        if not startTrans:
            startTrans = True
            outfile.write("\ttrans\n")
        outfile.write("\t\t")

        # from -> to
        if state_names == "id":
            outfile.write("%s%s -> %s%s" % (statePrefix, trans["src"],
                                            statePrefix, trans["dst"]))
        elif state_names == "hierarchical":
            outfile.write("%s%s -> %s%s" % (statePrefix,
                          chart.states[trans["src"]]["longName"],
                          statePrefix,
                          chart.states[trans["dst"]]["longName"]))
        else:
            outfile.write("%s%s -> %s%s" % (statePrefix,
                          chart.states[trans["src"]]["label"]["name"],
                          statePrefix,
                          chart.states[trans["dst"]]["label"]["name"]))

        outfile.write((" {"))
        
        conditions = []
        if trans["label"]["conditions"] != "":
            conditions.append(trans["label"]["conditions"])
        # negated conditions of transitions with higher priority
        for trans2 in chart.transitions:
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
        actionList = []
        if trans["label"]["ca"] != "":
            actionList.append(trans["label"]["ca"])
        for action in chart.states[trans["src"]]["label"]["ex"]:
            actionList.append(action)
        if trans["label"]["ta"] != "":
            actionList.append(trans["label"]["ta"])
        for action in chart.states[trans["dst"]]["label"]["en"]:
            actionList.append(action)
        actionString = " ".join(actionList)
        if actionString != "":
            if actionString[-1] == ',':
                actionString = actionString[:-1]
            outfile.write(" effect %s;" % actionString)
        
        outfile.write(" }\n")
        
    # during actions (transitions)
    for stateSSID, state in chart.states.items():
        for action in state["label"]["du"]:
            if not startTrans:
                startTrans = True
                outfile.write("\ttrans\n")
            outfile.write("\t\t")
                
            # from -> to
            if state_names == "id":
                outfile.write("%s%s -> %s%s" % (statePrefix, stateSSID,
                                                statePrefix, stateSSID))
            elif state_names == "hierarchical":
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
            for trans in chart.transitions:
                if (trans["src"] == stateSSID):
                    if trans["label"]["conditions"] != "":
                        conditions.append("not(" + trans["label"]["conditions"] + ")")
                    else:
                        conditions.append("false")
            if conditions != []:
                outfile.write(" guard %s;" % ", ".join(conditions))

            # actions
            actionList = []
            for action in state["label"]["du"]:
                actionList.append(action)
            actionString = " ".join(actionList)
            if actionString != "":
                if actionString[-1] == ',':
                    actionString = actionString[:-1]
                outfile.write(" effect %s;" % actionString)

            outfile.write(" }\n")

    outfile.write("}\n\n")
    
    # TODO
    outfile.write("system async;\n\n")

def sf2dve(infile, outfile, state_names):
    stateflowEtree = etree.parse(infile)
    checkInput(stateflowEtree)
    
    charts = []
    for chart in stateflowEtree.findall("Stateflow/machine/Children/chart"):
        charts.append(planarization.makePlanarized(chart))
    
    for varEl in stateflowEtree.findall("//machine/Children/data"):
        outfile.write(getDataVariable(varEl) + ";\n")
    
    for chart in charts:
        writeProcess(chart, outfile, state_names)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input Stateflow XML file",
                        type=argparse.FileType('r'))
    parser.add_argument("output", help="output DVE file",
                        type=argparse.FileType('w'))
    parser.add_argument("-s", "--state-names", help="as name of state " +\
                        "will be used: id (unique but not human friendly), " +\
                        "hierarchical name (longer, may not be unique) or " +\
                        "original name (shorter, may not be unique). Use " +\
                        "id (default) when generating input for DiVinE. " +\
                        "Also affects names of processes.",
                        choices=["id", "hierarchical", "name"], default="id")
    args = parser.parse_args()
    
    try:
        sf2dve(args.input, args.output, args.state_names)
    except notSupportedException as e:
        print("Following is not supported: %s" % e, file=sys.stderr)
        return
    except invalidInputException as e:
        print("Input is not valid stateflow: %s" % e, file=sys.stderr)
        return

if __name__ == "__main__":
    sys.exit(main())
