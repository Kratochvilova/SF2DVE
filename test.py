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

# TODO: on event actions and bind actions
#       Also, in MATLAB expressions there can be allmost anything, so this is
#       going to be hard. For now, I will use something less robust but easier
#       and will do this part later.
def parseLabel(label):
    actionKeywords = "(entry:|during:|exit:)"  
    
    if (label == None or label.findtext(".") == ""):    
        return ""
    
    newLabel = label.findtext(".") 
    temp = re.match(r"[^\n]*/((.|\n)*)", newLabel).group(1)  
    if (temp != None):
        newLabel = "entry:" + temp
    else:
        temp = re.match(r"[^\n]*\n((.|\n)*)", newLabel).group(1)
        if (temp != None):
            newLabel = temp
        else:
            return ""
            
    # TODO: replace abreviations
    
    entryActions = ""
    duringActions = ""
    exitActions = ""
    for temp in re.findall(r"entry:((.|\n)*)" + actionKeywords, newLabel).group(1):
        entryActions += temp 
    for temp in re.findall(r"during:((.|\n)*)" + actionKeywords, newLabel).group(1):
        duringActions += temp 
    for temp in re.findall(r"exit:((.|\n)*)" + actionKeywords, newLabel).group(1):
        exitActions += temp 
    
    # TODO: procces '\n' and ';'

def writeStateActions(label, actionType, outf):
    if (label == None or label.findtext(".") == ""):    
        return
    
    if (actionType == "entry:"):
        abbreviation = "en:"
    elif (actionType == "during:"):
        abbreviation = "du:"
    elif (actionType == "exit:"):
        abbreviation = "ex:"
    else:
        abbreviation = "undefined"
    
    # TODO: there can be another action after ';' and there can be antry
    #       actions without the keyword "entry" or "en"
    for action in re.findall(actionType + "([^;]+)", label.findtext(".")):
        outf.write("effect ")
        outf.write(action.strip())
        # this is just wrong
        if (action[-1] != ';' and action[-2] != ';'):
            outf.write("; ")
    if (abbreviation != "undefined"):
        for action in re.findall(abbreviation + "([^;]+)", label.findtext(".")):
            outf.write("effect ")
            outf.write(action.strip())
            # this is just wrong
            if (action[-1] != ';' and action[-2] != ';'):
                outf.write("; ")

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
        # this is just wrong
        if (action[-1] != ';' and action[-2] != ';'):
            outf.write("; ")

def writeTransitionConditions(label, outf):
    if (label == None or label.findtext(".") == ""):    
        return
    
    for condition in re.findall("\[(.*)\]", label.findtext(".")):
        outf.write("guard ")
        outf.write(condition.strip())
        # this is just wrong
        if (condition[-1] != ';' and condition[-2] != ';'):
            outf.write("; ")        
            
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
            print(e, file=sys.stderr)
        
        # actions
        label = trans.find('P[@Name="labelString"]')
        writeTransitionActions(label, "condition", outf)
                
        label = tree.find('%s/state[@SSID="%s"]/P[@Name="labelString"]' % (path, src))        
        writeStateActions(label, "exit:", outf)
                
        label = trans.find('P[@Name="labelString"]')
        writeTransitionActions(label, "action", outf)
                
        label = tree.find('%s/state[@SSID="%s"]/P[@Name="labelString"]' % (path, dst))
        writeStateActions(label, "entry:", outf)
        
        outf.write("}")        
        outf.write(",\n")
        
    # during actions (transitions)
    for state in tree.findall("%s/state" % path):        
        label = state.find('P[@Name="labelString"]')
        if (label != None and re.search("during:", label.findtext(".")) != None):
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


