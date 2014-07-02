#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 15 21:30:39 2014

@author: pavla
"""

import sys
import re
from lxml import etree

# for now there is just this one exception for any kind of unsupported 
# stateflow constructions
class notSupportedException(Exception): pass

# TODO: C syntax
#       detect wrong syntax (MATLAB)
#       replace ';' and '\n' for ','
def parseStateLabel(label):
    if (label == None or label.findtext(".") == ""):    
        return ""
    
    # deleting name and giving "entry:" before possible entry actions after '/'
    newLabel = label.findtext(".")
    match = re.match(r"[^\n]*/((.|\n)*)", newLabel)
    if (match != None):
        newLabel = "entry:" + match.group(1)
    else:
        match = re.match(r"[^\n]*\n((.|\n)*)", newLabel)
        if (match != None):
            newLabel = match.group(1)
        else:
            return ""
            
    # replacing abreviations
    newLabel.replace("en:", "entry:") 
    newLabel.replace("du:", "during:")
    newLabel.replace("ex:", "exit:")
    
    actionKeywords = "(entry:|during:|exit:)"
    
    # determining intervals of actions of one type
    limits = [m.start() for m in re.finditer(actionKeywords, newLabel)]
    limits.sort()
    limits.append(-1)
    intervals = []
    temp = None
    for limit in limits:
        if (temp != None):
            intervals.append((temp, limit))
        temp = limit
    
    entryActions = ""
    duringActions = ""
    exitActions = ""        
    
    for interval in intervals:
        if newLabel[interval[0]:].startswith("entry:"):
            entryActions += newLabel[interval[0]+len("entry:"):interval[1]] 
        elif newLabel[interval[0]:].startswith("during:"):
            duringActions += newLabel[interval[0]+len("during:"):interval[1]]
        elif newLabel[interval[0]:].startswith("exit:"):
            exitActions += newLabel[interval[0]+len("exit:"):interval[1]]
    
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
    
    action = re.search(actionType + r"((.|\n)*)" + nextType, label)
    if (action.group(1).strip() != ""):
        outf.write("effect ")
        outf.write(action.group(1).strip())

def writeTransitionActions(label, actionType, outf):
    if (label == None or label.findtext(".") == ""):    
        return
    
    if actionType == "condition":
        part = 0;
    elif actionType == "action":
        part = 1
        
    for action in re.findall("{(.*)}", label.findtext(".").split("/")[part]):
        outf.write("effect ")
        outf.write(action.strip())

def writeTransitionConditions(label, outf):
    if (label == None or label.findtext(".") == ""):    
        return
    
    for condition in re.findall("\[(.*)\]", label.findtext(".")):
        outf.write("guard ")
        outf.write(condition.strip())
            
def main(infile, outfile):
    tree = etree.parse(infile)
    outf = open(outfile, 'w')

    # system, TODO: check for syntax; check if stateflow is allways synchronous
    #               or something like that and if not, try to resolve this
    outf.write("system sync;\n\n")
    
    # properties, TODO: check for syntax; make it somehow intelligent, this
    #                   is just for now
    outf.write("property assert: assertion safety\n\n")
        
    path = "Stateflow/machine/Children/chart/Children"

    # process Process_X {
    outf.write("process Process_")
    outf.write(tree.find("Stateflow/machine").get("id"))
    outf.write(" {\n")
    
    # state 1, 2, 3, ... ;
    outf.write("\tstate init, ")
    outf.write(", ".join([state.get("SSID") for state in tree.findall("%s/state" % path)]))
    outf.write(";\n")   

    # init init;
    outf.write("\tinit init;\n")    
    
    # transitions (without loops representing during actions)
    # TODO: can there be a "guard" string before every guard and "effect" string 
    #       before every effect or is it necessary to have only one?
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
            outf.write(src)
        outf.write(" -> ")
        dst = trans.findtext('dst/P[@Name="SSID"]')
        outf.write(dst)
        
        outf.write((" { "))
        # conditions, TODO: condition actions should perhapse take place
        #                   even if condition is false
        label = trans.find('P[@Name="labelString"]')
        writeTransitionConditions(label, outf)
        try:
            if (label != None and re.search("{(.*)}", label.findtext(".").split("/")[0]) != None):
                raise notSupportedException("Warning: there is condition " 
                "action on transition %s. They are not supported (yet), so "
                "this may cause wrong behaviour. They will be considered as "
                "normal actions and will take place before exit action of "
                "source state (only when transition is taken)."
                % trans.get("SSID"))
        except notSupportedException as e:
            print(e)
        
        # actions
        label = trans.find('P[@Name="labelString"]')
        writeTransitionActions(label, "condition", outf)
        
        label = tree.find('%s/state[@SSID="%s"]/P[@Name="labelString"]' % (path, src))        
        label = parseStateLabel(label)        
        writeStateActions(label, "exit:", outf)
        
        label = trans.find('P[@Name="labelString"]')
        writeTransitionActions(label, "action", outf)
        
        label = tree.find('%s/state[@SSID="%s"]/P[@Name="labelString"]' % (path, dst))
        label = parseStateLabel(label)
        writeStateActions(label, "entry:", outf)
        
        outf.write("}")
        outf.write(",\n")
        
    # during actions (transitions)
    for state in tree.findall("%s/state" % path):
        label = state.find('P[@Name="labelString"]')
        label = parseStateLabel(label)

        if (label != None and 
            re.search(r"during:((.|\n)*)exit:", label).group(1).strip() != ""):
            outf.write("\t\t")
            
            # from -> to
            ssid = state.get("SSID")
            outf.write("%s -> %s" % (ssid, ssid))
            
            outf.write((" { "))
            # TODO: conditions - should there be some condition? Or maybe 
            #       somehow simulate events?           
            
            # actions
            writeStateActions(label, "during:", outf)            
            
            outf.write("}")        
            outf.write(",\n")
    
    
    outf.write("}\n")
    
    outf.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    else:
        sys.exit(1)


