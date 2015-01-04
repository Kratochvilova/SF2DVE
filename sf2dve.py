#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys, re, planarization
from lxml import etree
from extendedExceptions import notSupportedException, invalidInputException

processPrefix = "process_"
statePrefix = "state_"

# Checks action language, number of machines and state labels.
def checkInput(stateflowEtree):
    for chart in stateflowEtree.findall("Stateflow/machine/Children/chart"):
        actionLanguageSetting = chart.find('P[@Name="actionLanguage"]')
        if (actionLanguageSetting != None and
            actionLanguageSetting.findText(".") == "2"):
            raise invalidInputException("invalid action language")

    if (len(stateflowEtree.findall("Stateflow/machine")) != 1):
        raise invalidInputException("invalid number of machines")
        
    if stateflowEtree.find("//event") is not None:
        raise notSupportedException("events")

    for state in stateflowEtree.findall("//state"):
        if (state.find('P[@Name="labelString"]') is None or
            state.findtext('P[@Name="labelString"]') == ""):
            raise invalidInputException("state without label")

def getListOfStates(states, state_names):
    if state_names == "id":
        return ", ".join(statePrefix + ssid for ssid in states)
    elif state_names == "hierarchical":
        return ", ".join(statePrefix + s["longName"] for s in states.values())
    else:
        return ", ".join(statePrefix + s["label"]["name"] for s in states.values())

def getDataVariable(varEl):
    typeConversions = {"int":["int16", "int32", "uint8", "uint16", "uint32", 
                              "int"],
                       "byte":["int8", "boolean"]}

    varDef = {}

    varType = varEl.findtext('P[@Name="dataType"]')
    if varType in typeConversions["int"]:
        varDef["type"] = "int"
    elif varType in typeConversions["byte"]:
        varDef["type"] = "byte"
    else:
        raise notSupportedException("Variable of unsupported type: %s %s"
                                    % (varType, varEl.get("name")))

    varScope = varEl.findtext('P[@Name="scope"]')
    if varScope == "LOCAL_DATA" or varScope == "OUTPUT_DATA":
        varDef["scope"] = "local"
    elif varScope == "INPUT_DATA":
        varDef["scope"] = "input"
    elif varScope == "CONSTANT":
        varDef["const"] = True
    else:
        raise notSupportedException("Variable of unsupported scope: %s %s"
                                    % (varScope, varEl.get("name")))

    initialValueEl = varEl.find('props/P[@Name="initialValue"]')
    if initialValueEl != None:
        varDef["init"] = initialValueEl.findtext(".")
    else:
        varDef["init"] = None

    return (varEl.get("name"), varDef)

def writeProcess(chart, outfile, state_names, feed_input):
    # process declaration
    if state_names == "id":
        outfile.write("process %s%s {\n" % (processPrefix, chart.chartID))
    else:
        outfile.write("process %s%s {\n" % (processPrefix, chart.chartName))

    # variables
    for varName, varDef in chart.variables.items():
        if feed_input and varDef["scope"] == "input":
            continue
        outfile.write("\t")
        if varDef["scope"] == "input":
            outfile.write("input ")
        outfile.write("%s %s" % (varDef["type"], varName))
        if varDef["init"] != None and varDef["init"] != "":
            outfile.write(" = %s;\n" % varDef["init"])
        outfile.write(";\n")

    # states
    outfile.write("\tstate %s;\n" % getListOfStates(chart.states, state_names))
    outfile.write("\tinit %sstart;\n" % statePrefix)

    # transitions (without loops emulating during actions)
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
            (trans2["srcHierarchy"] < trans["srcHierarchy"] or
            (trans2["srcHierarchy"] == trans["srcHierarchy"] and
            trans2["transType"] < trans["transType"]) or
            (trans2["srcHierarchy"] == trans["srcHierarchy"] and
            (trans2["transType"] == trans["transType"] and
            trans2["order"] < trans["order"])))):
                if trans2["label"]["conditions"] != "":
                    conditions.append("not(" + trans2["label"]["conditions"] + ")")
                else:
                    conditions.append("false")

        if feed_input and conditions != []:
            outfile.write(" guard tick, %s;" % ", ".join(conditions))
        elif feed_input:
            outfile.write(" guard tick;")
        elif conditions != []:
            outfile.write(" guard %s;" % ", ".join(conditions))

        # actions
        actionList = []
        if trans["label"]["ca"] != "":
            actionList.append(trans["label"]["ca"])
        for action in chart.states[trans["src"]]["label"]["ex"]:
            actionList.append(action)
        if trans["label"]["ta"] != []:
            actionList += trans["label"]["ta"]
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
            if feed_input and conditions != []:
                outfile.write(" guard tick, %s;" % ", ".join(conditions))
            elif conditions != []:
                outfile.write(" guard %s;" % ", ".join(conditions))
            elif feed_input:
                outfile.write(" guard tick;")

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

def writeProcessFeedInputs(outfile, charts):
    byteVars = []
    intVars = []
    for chart in charts:
        for varName, varDef in chart.variables.items():
            if varDef["scope"] == "input":
                outfile.write("%s %s;\n" % (varDef["type"], varName))
                if varDef["type"] == "byte":
                    byteVars.append(varName)
                else:
                    intVars.append(varName)

    if intVars == [] and byteVars == []:
        return

    outfile.write("byte tick = 1;\n")
    
    outfile.write("\nprocess feed_inputs {\n")
    outfile.write("\tstate start;\n\tinit start;\n\ttrans\n")

    if intVars == []:
        lastVar = byteVars[-1]
    else:
        lastVar = intVars[-1]
    for i in range(0, 8**len(intVars) * 2**len(byteVars)):
        l = i
        outfile.write("\t\tstart -> start { effect tick = 1, ")
        for varName in byteVars:
            outfile.write("%s = %s" % (varName, int(l % 2)))
            l = (l - l % 2) / 2
            if varName != lastVar:
                outfile.write(", ")
        for varName in intVars:
            outfile.write("%s = %s" % (varName, int(l % 8)))
            l = (l - l % 8) / 8
            if varName != lastVar:
                outfile.write(", ")
        outfile.write("; }\n")
    outfile.write("}\n\n")

def sf2dve(infile, outfile, state_names, feed_input):
    stateflowEtree = etree.parse(infile)
    checkInput(stateflowEtree)

    charts = []
    for chart in stateflowEtree.findall("Stateflow/machine/Children/chart"):
        charts.append(planarization.makePlanarized(chart))

    if feed_input:
        writeProcessFeedInputs(outfile, charts)

    for chart in charts:
        writeProcess(chart, outfile, state_names, feed_input)

    # TODO
    outfile.write("system async;\n\n")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input Stateflow XML file",
                        type=argparse.FileType('r'))
    parser.add_argument("output", help="output DVE file",
                        type=argparse.FileType('w'))
    parser.add_argument("-n", "--state-names", help="as name of state " +\
                        "will be used: id (unique but not human friendly), " +\
                        "hierarchical name (longer, may not be unique) or " +\
                        "original name (shorter, may not be unique). Use " +\
                        "id (default) when generating input for DiVinE. " +\
                        "Also affects names of processes.",
                        choices=["id", "hierarchical", "name"], default="id")
    parser.add_argument("-i", "--feed-input", help="this option adds " +\
                        "process that nondeterministically feeds input " +\
                        "variables from interval <0, 7> (or <0, 1> for " +\
                        "bytes). Also adds variable tick.", 
                        action='store_true', 
                        default=False)
    args = parser.parse_args()
    
    try:
        sf2dve(args.input, args.output, args.state_names, args.feed_input)
    except notSupportedException as e:
        print("Following is not supported: %s" % e, file=sys.stderr)
        return
    except invalidInputException as e:
        print("Input is not valid stateflow: %s" % e, file=sys.stderr)
        return

if __name__ == "__main__":
    sys.exit(main())
