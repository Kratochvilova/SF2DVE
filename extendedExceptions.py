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
Created on Sun Nov 30 19:59:18 2014

@author: pavla
"""

# exception for any kind of unsupported stateflow constructions
class notSupportedException(Exception): pass

class invalidInputException(Exception): pass
    