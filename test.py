#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys
import re
from lxml import etree

path = "Stateflow/machine/Children/chart/Children"
processPrefix = "process_"
statePrefix = "state_"
actionKeywords = "(entry:|during:|exit:)"

# exception for any kind of unsupported stateflow constructions
class notSupportedException(Exception): pass


# TODO: plannarization
class plannarized():
    pass

def plannarize(tree):
    pass



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

def writeTransitionActions(labelElement, actionType, outf):
    if (labelElement == None or labelElement.findtext(".") == ""):
        return
    
    if (len(labelElement.findtext(".").split("/")) == 1 and actionType == "action"):
        return
        
    if actionType == "condition":
        part = 0
    elif actionType == "action":
        part = 1
    
    for action in re.findall("{(.*)}", labelElement.findtext(".").split("/")[part]):
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

def writeTransitionConditions(labelElement, outf, negation):
    if (labelElement == None or labelElement.findtext(".") == ""):
        # if negation is true, there shoud be raised exception or returned 
        # something that would indicate, what's happend (this means that there
        # is transition that cannot be taken)
        return

    conditions = " and ".join(repareCondition(condition.strip()) for condition 
        in re.findall("\[(.*)\]", labelElement.findtext(".").split("/")[0]))

    if (conditions != ""):
        if (negation):
            outf.write(" guard not(%s)" % conditions)
        else:
            outf.write(" guard %s" % conditions)
        if (conditions[-1] != ';'):
            outf.write(';')

def getStateName(labelElement):
    if (labelElement == None or labelElement.findtext(".") == ""):    
        return ""
    
    match = re.match(r"([^\n]*)/", labelElement.findtext("."))
    if (match != None):
        return match.group(1).strip()
    else:
        match = re.match(r"([^\n]*)\n", labelElement.findtext("."))
        if (match != None):
            return match.group(1).strip()
    return ""             
         
def main(infile, outfile):
    tree = etree.parse(infile)
    
    # there should be some input validation
    # (there should be language setting (MATLAB or nothing) somewhere in 
    # ModelInformation.Model.ConfigurationSet.Array.Object.Array.Object)
    
    outf = open(outfile, 'w')
    
    # system, TODO: check syntax; check if stateflow is allways synchronous
    #               or something like that and if not, try to resolve this
    outf.write("system sync;\n\n")
    
    # properties, TODO: check syntax; make it somehow intelligent, this is
    #                   just for now
    outf.write("property true\n\n")
        
    path = "Stateflow/machine/Children/chart/Children"

    # process
    outf.write("process %s%s {\n" % (processPrefix, 
                                     tree.find("Stateflow/machine").get("id")))

    # variables
    for var in tree.findall("%s/data" % path):
        outf.write("\t%s %s;\n" % (var.findtext('P[@Name="dataType"]'), var.get("name")))

    # states
    outf.write("\tstate init, ")
    outf.write(", ".join(statePrefix + state.get("SSID") for state in 
                         tree.findall("%s/state" % path)))
    outf.write("; ")
    #outf.write("// States are named by their SSID (with exception of "
    #           "additional state init). Corresponding names are as follows: ")
    #for state in tree.findall("%s/state" % path):
    #    labelElement = state.find('P[@Name="labelString"]')
    #    outf.write("%s%s - %s; " % (statePrefix, state.get("SSID"), 
    #                                getStateName(labelElement)))
    outf.write("\n")

    # initial state
    outf.write("\tinit init;\n")    
    
    # transitions (without loops representing during actions)
    # TODO: can there be a "guard" string before every guard and "effect"  
    #       string before every effect or is it necessary to have only one?
    #       Can there be ';' after the last guards and effects?
    #       Can there be ',' after the last transition?
    outf.write("\ttrans\n")   
    transitions = tree.findall("%s/transition" % path)
    for trans in transitions:
        outf.write("\t\t")
        
        # from -> to
        src = trans.findtext('src/P[@Name="SSID"]')
        if (src == None):
            outf.write("init")
        else:
            outf.write(statePrefix)
            outf.write(src)
        outf.write(" -> ")
        dst = trans.findtext('dst/P[@Name="SSID"]')
        outf.write(statePrefix)
        outf.write(dst)
        
        outf.write((" {"))
        # conditions, TODO: condition actions should perhaps take place even 
        #                   if condition is false - need to find out!
        labelElement = trans.find('P[@Name="labelString"]')
        writeTransitionConditions(labelElement, outf, False)
        try:
            if (labelElement != None and 
                re.search("{(.*)}", labelElement.findtext(".").split("/")[0]) 
                != None):
                raise notSupportedException("Warning: there is condition " 
                "action on transition %s. They are not supported (yet), so "
                "this may cause wrong behaviour. They will be considered as "
                "normal actions and will take place before exit action of "
                "source state (only when transition is taken)."
                % trans.get("SSID"))
        except notSupportedException as e:
            print(e)
        
        # negated conditions of transitions with higher priority - this should
        # guarantee that conditions 
        # solve priorities in case of conflicting transitions
        executionOrder = trans.find('P[@Name="executionOrder"]').findtext(".")
        if (executionOrder != "1"):
            print("priorities! transition %s" % trans.get("SSID"))
            for trans2 in transitions:
                executionOrder2 = trans2.find('P[@Name="executionOrder"]').findtext(".")
                src2 = trans2.findtext('src/P[@Name="SSID"]')                
                if (src2 == src and executionOrder2 < executionOrder):
                    writeTransitionConditions(trans2.find('P[@Name="labelString"]'), outf, True)
        
        # actions
        labelElement = trans.find('P[@Name="labelString"]')
        writeTransitionActions(labelElement, "condition", outf)
        
        labelElement = tree.find('%s/state[@SSID="%s"]/P[@Name="labelString"]' 
                          % (path, src))
        if (labelElement != None):
            label = labelElement.findtext(".")
            label = parseStateLabel(label)        
            writeStateActions(label, "exit:", outf)
        
        labelElement = trans.find('P[@Name="labelString"]')
        writeTransitionActions(labelElement, "action", outf)
        
        labelElement = tree.find('%s/state[@SSID="%s"]/P[@Name="labelString"]' 
                          % (path, dst))
        if (labelElement != None):
            label = labelElement.findtext(".")
            label = parseStateLabel(label)
            writeStateActions(label, "entry:", outf)
        
        outf.write(" }")
        outf.write(",\n")
        
    # during actions (transitions)
    for state in tree.findall("%s/state" % path):
        labelElement = state.find('P[@Name="labelString"]')
        if (labelElement != None):
            label = labelElement.findtext(".")
        else:
            label = ""    
        label = parseStateLabel(label)

        if (re.search(r"during:((.|\n)*)exit:", label).group(1).strip() != ""):
            outf.write("\t\t")
            
            # from -> to
            ssid = state.get("SSID")
            outf.write("%s%s -> %s%s" % (statePrefix, ssid, statePrefix, ssid))
            
            outf.write((" {"))
            # conditions
            for trans in transitions:
                src = trans.findtext('src/P[@Name="SSID"]')                
                if (src == ssid):
                    writeTransitionConditions(trans.find('P[@Name="labelString"]'), outf, True)
            
            # actions
            writeStateActions(label, "during:", outf)            
            
            outf.write(" }")        
            outf.write(",\n")
    
    
    outf.write("}\n")
    
    outf.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    else:
        sys.exit(1)


