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
Created on Sat Dec 27 14:10:02 2014

@author: pavla
"""

import sys, subprocess, re

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="DVE file; with additional process " +\
                        "feed_inputs", type=argparse.FileType('r'))
    parser.add_argument("input", help="file with input sequence for each " +\
                        "input variable. Each variable is on new line and " +\
                        "in format: variable_name = [n1 n2 n3 ...]", 
                        type=argparse.FileType('r'))
    parser.add_argument("output", help="output file for storing sequence " +\
                        "of values of variable ControlVector", 
                        type=argparse.FileType('w'))
    args = parser.parse_args()
    
    byteVars = []
    intVars = []
    
    for line in args.input:
        varName = re.search(r"(.+)\[", line).group(1).strip()
        varInputs = re.search(r"\[(.+)\]", line).group(1).strip().split()
        
        for varInput in varInputs:
            intVar = False
            if varInput != '0' and varInput != '1':
                intVar = True
                break
        if intVar:
            intVars.append((varName, varInputs))
        else:
            byteVars.append((varName, varInputs))
    
    if byteVars != []:
        maxInput = len(byteVars[0][1])
    else:
        maxInput = len(intVars[0][1])    
    
    inputTrace = "--trace=1,"
    maxVarCom = 8**len(intVars) * 2**len(byteVars)
    firstCatched = False    
    
    for i in range(0, maxInput):
        for j in range(0, maxVarCom):
            l = j
            match = True
            for varName, varInputs in byteVars:
                if varInputs[i] != str(int(l % 2)):
                    match = False
                l = (l - l % 2) / 2
            for varName, varInputs in intVars:
                if varInputs[i] != str(int(l % 8)):
                    match = False
                l = (l - l % 8) / 8
            if match:
                if firstCatched:
                    inputTrace += str(j + 1) + ","
                else:
                    firstCatched = True
                break
        inputTrace += str(maxVarCom + 1) + ","
    
    inputTrace = inputTrace[:-1]

    p = subprocess.Popen(["divine", "simulate", inputTrace, args.model.name], 
                         stdout=subprocess.PIPE, stderr=open("/dev/null", "w"))
    
    blocks = []
    block = []
    first = True
    for line in p.stdout.readlines():
        line = line.decode()
        block.append(line)
        if line == "\n":
            if not block[0].startswith("=> feed_inputs") and not first:
                blocks.append(block)
            block = []
            first = False

    blocks = blocks[1:]

    output_sequence = ""
    for block in blocks:
        for line in block:
            if line.startswith("process_"):
                number = re.search("ControlVector = ([^,]+)", line).group(1)
                output_sequence += number + "\n"

    args.output.write(output_sequence)

if __name__ == "__main__":
    sys.exit(main())
