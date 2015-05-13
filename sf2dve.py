#!/usr/bin/env python3
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
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys, re, zipfile
from lxml import etree
from copy import copy
from extendedExceptions import notSupportedException, invalidInputException

processPrefix = "process_"
statePrefix = "state_"

# Checks action language, number of machines and state labels.
def checkInput(stateflowEtree):
    if stateflowEtree.find("Stateflow") is None:
        raise invalidInputException("not recognized as Stateflow")

    if len(stateflowEtree.findall("Stateflow/machine")) != 1:
        raise invalidInputException("invalid number of machines")

    for chart in stateflowEtree.findall("Stateflow/machine/Children/chart"):
        actionLanguageSetting = chart.find('P[@Name="actionLanguage"]')
        if (actionLanguageSetting != None and
            actionLanguageSetting.findtext(".") == "2"):
            raise invalidInputException("invalid action language")

    if stateflowEtree.find("//event") is not None:
        raise notSupportedException("events")

    if stateflowEtree.find("//junction") is not None:
        raise notSupportedException("junctions")

    for state in stateflowEtree.findall("//state"):
        if (state.find('P[@Name="labelString"]') is None or
            state.findtext('P[@Name="labelString"]') == ""):
            raise invalidInputException("state without label")
        stateType = state.findtext('P[@Name="type"]')
        if stateType != "OR_STATE":
            if stateType == "AND_STATE":
                raise notSupportedException("and decomposition of states")
            elif stateType == "FUNC_STATE":
                raise notSupportedException("functions")
            else:
                raise notSupportedException("state of type %s" % stateType)

def getStateID(ssid, states, state_names):
    if state_names == "id" or ssid == "start" or ssid == "error":
        return statePrefix + ssid
    elif state_names == "hierarchical":
        return statePrefix + states[ssid]["longName"]
    else:
        return statePrefix + states[ssid]["label"]["name"]

def writeProcess(chart, outfile, state_names, input_values):
    from planarization import negateConditions
    # process declaration
    if state_names == "id":
        outfile.write("process %s%s {\n" % (processPrefix, chart.chartID))
    else:
        outfile.write("process %s%s {\n" % (processPrefix, chart.chartName))

    # variables
    for varName, varDef in chart.variables.items():
        if input_values is not None and varDef["scope"] == "input":
            continue
        outfile.write("\t")
        if varDef["scope"] == "input":
            outfile.write("input ")
        if varDef["const"]:
            outfile.write("const ")
        outfile.write("%s %s" % (varDef["type"], varName))
        if varDef["init"] != None and varDef["init"] != "":
            outfile.write(" = %s" % varDef["init"])
        outfile.write(";\n")

    # states
    stateList = [getStateID(ssid, chart.states, state_names) for ssid in chart.states]
    outfile.write("\tstate %s;\n" % ", ".join(stateList))
    outfile.write("\tinit %sstart;\n" % statePrefix)

    # transitions (without loops emulating during actions)
    startTrans = False
    for trans in chart.transitions:
        if not startTrans:
            startTrans = True
            outfile.write("\ttrans\n")
        outfile.write("\t\t")

        # from -> to
        source = getStateID(trans["src"], chart.states, state_names)
        destination = getStateID(trans["dst"], chart.states, state_names)
        outfile.write("%s -> %s" % (source, destination))

        outfile.write((" {"))

        # conditions and negated conditions of transitions with higher priority
        conditions = copy(trans["conditions"])
        for trans2 in chart.transitions:
            if (trans2["src"] == trans["src"] and
            (trans2["srcHierarchy"] < trans["srcHierarchy"] or
            (trans2["srcHierarchy"] == trans["srcHierarchy"] and
            trans2["transType"] < trans["transType"]) or
            (trans2["srcHierarchy"] == trans["srcHierarchy"] and
            (trans2["transType"] == trans["transType"] and
            trans2["order"] < trans["order"])))):
                conditions.append(negateConditions(trans2["conditions"]))
        if conditions != []:
            outfile.write(" guard %s;" % ", ".join(conditions))

        # actions
        if trans["actions"] != []:
            outfile.write(" effect %s;" % ", ".join(trans["actions"]))

        outfile.write(" }\n")

    # during actions
    for stateSSID, state in chart.states.items():
        if state["label"]["du"] != []:
            if not startTrans:
                startTrans = True
                outfile.write("\ttrans\n")

            outfile.write("\t\t")

            # from -> to
            stateID = getStateID(stateSSID, chart.states, state_names)
            outfile.write("%s -> %s" % (stateID, stateID))

            outfile.write((" {"))

            # conditions
            conditions = []
            for trans in filter(lambda x:x["src"] == stateSSID, chart.transitions):
                conditions.append(negateConditions(trans["conditions"]))
            if conditions != []:
                outfile.write(" guard %s;" % ", ".join(conditions))

            # actions
            outfile.write(" effect %s;" % ", ".join(state["label"]["du"]))

            outfile.write(" }\n")

    outfile.write("}\n\n")

def writeProcessFeedInputs(outfile, charts, input_values):
    byteMin = 0
    byteMax = 1
    intMin = input_values[0]
    intMax = input_values[1]
    byteSize = byteMax - byteMin + 1
    intSize = intMax - intMin + 1
    
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

    outfile.write("\nprocess feed_inputs {\n")
    outfile.write("\tstate start;\n\tinit start;\n\ttrans\n")

    if intVars == []:
        lastVar = byteVars[-1]
    else:
        lastVar = intVars[-1]
    for i in range(0, intSize**len(intVars) * byteSize**len(byteVars)):
        l = i
        outfile.write("\t\tstart -> start { effect ")
        for varName in byteVars:
            outfile.write("%s = %s" % (varName, int(l % byteSize + byteMin)))
            l = (l - l % byteSize) / byteSize
            if varName != lastVar:
                outfile.write(", ")
        for varName in intVars:
            outfile.write("%s = %s" % (varName, int(l % intSize) + intMin))
            l = (l - l % intSize) / intSize
            if varName != lastVar:
                outfile.write(", ")
        outfile.write("; }\n")
    outfile.write("}\n\n")

def sf2dve(infile, outfile, state_names, input_values):
    from planarization import makePlanarized
    try:
        stateflowEtree = etree.parse(infile)
    except:
        raise invalidInputException("failed to parse XML")
    checkInput(stateflowEtree)

    charts = []
    for chart in stateflowEtree.findall("Stateflow/machine/Children/chart"):
        charts.append(makePlanarized(chart))

    if input_values is not None:
        writeProcessFeedInputs(outfile, charts, input_values)

    for chart in charts:
        writeProcess(chart, outfile, state_names, input_values)

    outfile.write("system async;\n\n")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input Stateflow SLX or XML file",
                        type=argparse.FileType('rb'))
    parser.add_argument("output", help="output DVE file; if not set, name " +\
                        "of input file with dve suffix will be used",
                        type=argparse.FileType('w'), nargs='?')
    parser.add_argument("-n", "--state-names", help="as name of state " +\
                        "will be used: id (unique but not human friendly), " +\
                        "hierarchical name (longer, may not be unique) or " +\
                        "original name (shorter, may not be unique). Use " +\
                        "id (default) when generating input for DiVinE. " +\
                        "Also affects names of processes.",
                        choices=["id", "hierarchical", "name"], default="id")
    parser.add_argument("-f", "--feed-input", help="this option adds " +\
                        "process that nondeterministically feeds input " +\
                        "variables with values from given interval, " +\
                        "<0,1> for bytes, <0,7> for integers.", 
                        action='store_true')
    parser.add_argument("-i", "--input-values", help="Similar to the option" +\
                        "--feed-inputs. For bytes the interval is <0,1>, " +\
                        "For integers the interval is to be specified with " +\
                        "the marginal numbers in format: 0,7 If the first " +\
                        "number is negative, use format: ' -7,7'", type=str, 
                        default=None)
    args = parser.parse_args()
    
    input_file = args.input
    output_file = args.output
    if output_file is None:
        if input_file == sys.stdin:
            output_file = sys.stdout
        else:
            try:
                output_file = open("%s.dve" % input_file.name.rsplit(".", 1)[0], 'w')
            except IOError as e:
                print("Can't open output file: %s" % e, file=sys.stderr)
                return 1
    if input_file != sys.stdin and zipfile.is_zipfile(input_file):
        try:
            input_file = zipfile.ZipFile(input_file).open("simulink/blockdiagram.xml")
        except KeyError:
            print("Couldn't find Stateflow XML file in given archive.", file=sys.stderr)
            return 1
    elif input_file != sys.stdin:
        # not zipfile, unfortunately is_zipfile doesn't seek back to
        # beginning so this needs to be done by hand (lxml.parse doesn't
        # seek either)
        input_file.seek(0)

    if args.input_values is not None:
        input_values = args.input_values.split(',')
        if len(input_values) != 2:
            print("Incorrect format of the interval: too many numbers", 
                  file=sys.stderr)
            return 1
        try:
            input_values = [int(input_values[0]), int(input_values[1])]
        except ValueError:
            print("Incorrect format of the interval: numbers not recognized", 
                  file=sys.stderr)
            return 1
        if input_values[0] > input_values[1]:
            print("Incorrect format of the interval: the first number must " +\
            "be lower then the second", file=sys.stderr)
            return 1
    elif args.feed_input is not None:
        input_values = [0, 7]
    else: input_values = None

    try:
        sf2dve(input_file, output_file, args.state_names, input_values)
    except notSupportedException as e:
        print("Following is not supported: %s" % e, file=sys.stderr)
        return 1
    except invalidInputException as e:
        print("Input is not valid stateflow: %s" % e, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
