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

# TODO: exceptions

# exception for any kind of unsupported stateflow constructions
class notSupportedException(Exception): pass

# TODO: initializing to 0?
class plannarized:
    machineID = 0
    states = {}
    transitions = []
    
def getStateName(labelElement):
    if (labelElement == None or labelElement.findtext(".") == ""):    
        return ""
    
    match = re.match(r"([^\n]*)/", labelElement.findtext("."))
    if (match != None):
        return match.group(1).strip()
    match = re.match(r"([^\n]*)\n", labelElement.findtext("."))
    if (match != None):
        return match.group(1).strip()
        
    return labelElement.findtext(".")

def makePlannarized(tree):
    stateflow = plannarized()

    # TODO: find out what is this machine (if it correspons with process in 
    # DVE and what to do it there are more or them)
    stateflow.machineID = tree.find("Stateflow/machine").get("id")    
    
    # storing leaf states of the state hierarchy (ssid, name, label, parents)
    # "init" is for future information whether there is some default transition
    for state in tree.findall("//state"):
        if (state.find("Children") == None):
            labelElement = state.find('P[@Name="labelString"]')
            if (labelElement == None):
                label = ""
            else:
                label = labelElement.findtext(".")
            label = parseStateLabel(label)
                
            parents = []
            name = getStateName(labelElement)
            parent = state.getparent().getparent()
            while (parent.tag == "state"):
                parents.append(parent.get("SSID"))
                name = getStateName(parent.find('P[@Name="labelString"]')) \
                       + "." + name
                parent = parent.getparent().getparent()
                
            stateflow.states[state.get("SSID")] = {"name":name, "label":label,
            "parents":parents, "init":False}
    
    # seting "init"
    for trans in tree.findall("//transition"):
        srcElement = trans.find('src/P[@Name="SSID"]')
        dst = trans.findtext('dst/P[@Name="SSID"]')
        if (srcElement == None and dst in stateflow.states.keys()):
            stateflow.states[dst]["init"] = True
        
    # storing transitions (label, source, destination, execution order)
    # (ssid doesn't make sence since there can be transition from superstate
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
        else:
            for stateSSID, state in stateflow.states.items():
                if (src in state["parents"]):
                    sources.append(stateSSID)
        
        if (dst in stateflow.states.keys()):
            destination = dst
        else:
            child = tree.find('//state[@SSID="%s"]' % dst)
            while (child.find("Children") != None):
                # TODO: this would be better, but for some reason these xpath
                # conditions won't work:
                # childTrans = child.find('Children/transition/src[not(P)]')
                for trans in child.findall("Children/transition"):
                    if (trans.find('src/P[@Name="SSID"]') == None):
                        childTrans = trans
                        break
                childSSID = childTrans.findtext('dst/P[@Name="SSID"]')
                child = child.find('Children/state[@SSID="%s"]' % childSSID)
            destination = childSSID
            
        order = trans.findtext('P[@Name="executionOrder"]')
        
        for source in sources:
            stateflow.transitions.append({"label":label, "src":source, 
            "dst":destination, "order":order})
    
    return stateflow
    
# TODO: C syntax
#       replace ';' and '\n' for ','
#       or divide sequence of actions into single actions
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

def writeStateActions(label, actionType, outf):
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
        outf.write(" effect %s" % action)
        if (action[-1] != ";"):
            outf.write(";")

# TODO: actions probably don't have to be in curly brackets - correct this
def writeTransitionActions(label, actionType, outf):
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
            outf.write(" effect %s" % action)
            if (action[-1] != ";"):
                outf.write(";")

def repareCondition(condition):
    if (condition == ""):
        return "true"
    else:
        return condition

# TODO: conditions probably don't have to be in brackets - correct this
def writeTransitionConditions(label, outf, positive):
    if (label == ""):
        # TODO: if positive is false, there shoud be raised exception or  
        # returned something that would indicate, what's happend (this means
        # that there is transition that cannot be taken)
        return

    conditions = " and ".join(repareCondition(condition.strip()) for condition 
        in re.findall("\[(.*)\]", label.split("/")[0]))

    if (conditions != ""):
        if (positive):
            outf.write(" guard %s" % conditions)
        else:
            outf.write(" guard not(%s)" % conditions)
        if (conditions[-1] != ';'):
            outf.write(';')

def main(infile, outfile):
    tree = etree.parse(infile)
    
    # TODO: there should be some input validation
    # (there should be language setting (MATLAB or nothing) somewhere in 
    # ModelInformation.Model.ConfigurationSet.Array.Object.Array.Object)
    
    outf = open(outfile, 'w')
    
    stateflow = makePlannarized(tree)
    
    # system
    # TODO: check syntax; check if stateflow is allways synchronous or
    #       something like that and if not, try to resolve this
    outf.write("system sync;\n\n")
    
    # properties
    # TODO: check syntax; make it somehow intelligent, this is just temporary
    outf.write("property true\n\n")

    # process
    outf.write("process %s%s {\n" % (processPrefix, stateflow.machineID))

    # variables
    # TODO: correct this and look for other types
    for var in tree.findall("%s/data" % path):
        varType = var.findtext('P[@Name="dataType"]')
        if (varType.startswith("uint")):
            outf.write("\tinteger %s;\n" % var.get("name"))
        if (varType == "boolean"):
            outf.write("\tbyte %s;\n" % var.get("name"))

    # states
    outf.write("\tstate init, ")
    outf.write(", ".join(statePrefix + ssid for ssid in 
                                            stateflow.states.keys()))
    outf.write(";\n")

    # TODO: find out how to write multiline comments and then maybe also write 
    #       this (or find another solution)
    #outf.write("\tStates are named by their SSID (with exception of additional "
    #           "state init). Corresponding names are as follows:\n")
    #for stateSSID, state in stateflow.states.items():
    #    outf.write("\t%s%s - %s\n" % (statePrefix, stateSSID, state["name"]))

    # initial state
    outf.write("\tinit init;\n")    
    
    # transitions (without loops representing during actions)
    # TODO: can there be a "guard" string before every guard and "effect"  
    #       string before every effect or is it necessary to have only one?
    #       Can there be ';' after the last guards and effects?
    #       Can there be ',' after the last transition?
    outf.write("\ttrans\n")   
    for trans in stateflow.transitions:
        outf.write("\t\t")
        
        # from -> to
        if (trans["src"] != "init"):
            outf.write(statePrefix)
        outf.write("%s -> %s%s" % (trans["src"], statePrefix, trans["dst"]))
        
        outf.write((" {"))
        # conditions, TODO: condition actions should perhaps take place even 
        #                   if condition is false - need to find out!
        writeTransitionConditions(trans["label"], outf, True)
        try:
            if (re.search("{(.*)}", trans["label"].split("/")[0]) != None):
                raise notSupportedException("Warning: condition action on " 
                "transition detected. They are not supported (yet), so "
                "this may cause wrong behaviour. They will be considered as "
                "normal actions and will take place before exit action of "
                "source state (only when transition is taken).")
        except notSupportedException as e:
            print(e)
        
        # negated conditions of transitions with higher priority - this should
        # solve priorities in case of conflicting transitions
        # TODO: comparing strings (trans2["order"] < trans["order"])?
        if (trans["order"] != "1"):
            for trans2 in stateflow.transitions:
                if (trans2["src"] == trans["src"] and 
                    trans2["order"] < trans["order"]):
                    writeTransitionConditions(trans2["label"], outf, False)
        
        # actions
        writeTransitionActions(trans["label"], "condition", outf)
        
        if (trans["src"] in stateflow.states.keys()):
            writeStateActions(stateflow.states[trans["src"]]["label"], 
                              "exit:", outf)
        
        writeTransitionActions(trans["label"], "action", outf)

        if (trans["dst"] in stateflow.states.keys()):     
            writeStateActions(stateflow.states[trans["dst"]]["label"] , 
                              "exit:", outf)
        
        outf.write(" }")
        outf.write(",\n")
        
    # during actions (transitions)
    for stateSSID, state in stateflow.states.items():
        if (re.search(r"during:((.|\n)*)exit:", 
                      state["label"]).group(1).strip() != ""):
            outf.write("\t\t")
            
            # from -> to
            outf.write("%s%s -> %s%s" % (statePrefix, stateSSID, statePrefix, 
                                         stateSSID))
            
            outf.write((" {"))
            # conditions
            for trans in stateflow.transitions:
                if (trans["src"] == stateSSID):
                    writeTransitionConditions(trans["label"], outf, False)
            
            # actions
            writeStateActions(state["label"], "during:", outf)            
            
            outf.write(" }")        
            outf.write(",\n")
    
    outf.write("}\n")
    
    outf.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    else:
        sys.exit(1)


