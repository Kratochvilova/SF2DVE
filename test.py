#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys
import re
from lxml import etree

processPrefix = "Process_"
statePrefix = "State_"
actionKeywords = "(entry:|during:|exit:)"

# for now there is just this one exception for any kind of unsupported 
# stateflow constructions
class notSupportedException(Exception): pass

# TODO: C syntax
#       replace ';' and '\n' for ',' 
#       or divide sequence of actions into single actions
def parseStateLabel(label):
    if (label == None or label == ""):    
        return ""
    
    # deleting name and puting "entry:" before possible entry actions after '/'
    match = re.match(r"[^\n]*/((.|\n)*)", label)
    if (match != None):
        label = "entry:" + match.group(1)
    else:
        match = re.match(r"[^\n]*\n((.|\n)*)", label)
        if (match != None):
            label = match.group(1)
        else:
            return ""
            
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
            entryActions += label[interval[0]+len("entry:"):interval[1]] 
        elif label[interval[0]:].startswith("during:"):
            duringActions += label[interval[0]+len("during:"):interval[1]]
        elif label[interval[0]:].startswith("exit:"):
            exitActions += label[interval[0]+len("exit:"):interval[1]]
    
    return ("entry:" + entryActions.strip() + 
            "during:" + duringActions.strip() + 
            "exit:" + exitActions.strip())

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

def writeTransitionConditions(labelElement, outf):
    if (labelElement == None or labelElement.findtext(".") == ""):
        return
    
    for condition in re.findall("\[(.*)\]", 
                                labelElement.findtext(".").split("/")[0]):
        condition = condition.strip()        
        if (condition != ""):
            outf.write(" guard %s" % condition)
            if (condition[-1] != ';'):
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
    outf = open(outfile, 'w')
    
    # system, TODO: check syntax; check if stateflow is allways synchronous
    #               or something like that and if not, try to resolve this
    outf.write("system sync;\n\n")
    
    # properties, TODO: check syntax; make it somehow intelligent, this is
    #                   just for now
    outf.write("property true\n\n")
        
    path = "Stateflow/machine/Children/chart/Children"

    # process Process_X {
    outf.write("process %s%s {\n" % (processPrefix, 
                                     tree.find("Stateflow/machine").get("id")))

    # state_1, state_2, state_3, ... ;
    outf.write("\tstate init, ")
    outf.write(", ".join(statePrefix + state.get("SSID") for state in 
                         tree.findall("%s/state" % path)))
    outf.write("; // States are named by their SSID. Corresponding names are "
               "as follows: ")
    for state in tree.findall("%s/state" % path):
        labelElement = state.find('P[@Name="labelString"]')
        outf.write("%s%s - %s; " % (statePrefix, state.get("SSID"), 
                                    getStateName(labelElement)))
    outf.write("\n")

    # init init;
    outf.write("\tinit init;\n")    
    
    # transitions (without loops representing during actions)
    # TODO: can there be a "guard" string before every guard and "effect"  
    #       string before every effect or is it necessary to have only one?
    #       Can there be ';' after the last guards and effects?
    #       Can there be ',' after the last transition?
    outf.write("\ttrans\n")
    for trans in tree.findall("%s/transition" % path):
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
        #                   if condition is false
        labelElement = trans.find('P[@Name="labelString"]')
        writeTransitionConditions(labelElement, outf)
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
            label = parseStateLabel(label)

        if (re.search(r"during:((.|\n)*)exit:", label).group(1).strip() != ""):
            outf.write("\t\t")
            
            # from -> to
            ssid = state.get("SSID")
            outf.write(statePrefix)
            outf.write(ssid)
            outf.write(" -> ")
            outf.write(statePrefix)
            outf.write(ssid)
            
            outf.write((" {"))
            # TODO: conditions - should there be some condition? Or maybe 
            #       somehow simulate events?
            
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


