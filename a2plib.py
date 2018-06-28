#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
#*                                                                         *
#*   Portions of code based on hamish's assembly 2                         *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import FreeCAD, FreeCADGui, Part
from PySide import QtGui, QtCore
import numpy, os
from viewProviderProxies import *
from  FreeCAD import Base


USE_PROJECTFILE = False

DEBUGPROGRAM = 1

path_a2p = os.path.dirname(__file__)
path_a2p_resources = os.path.join( path_a2p, 'GuiA2p', 'Resources', 'resources.rcc')
resourcesLoaded = QtCore.QResource.registerResource(path_a2p_resources)
assert resourcesLoaded



wb_globals = {}

RED = (1.0,0.0,0.0)
GREEN = (0.0,1.0,0.0)
BLUE = (0.0,0.0,1.0)

#------------------------------------------------------------------------------
def appVersionStr():
    version = int(FreeCAD.Version()[0])
    subVersion = int(FreeCAD.Version()[1])
    return "%03d.%03d" %(version,subVersion)
#------------------------------------------------------------------------------
def isLine(param):
    if hasattr(Part,"LineSegment"):
        return isinstance(param,(Part.Line,Part.LineSegment))
    else:
        return isinstance(param,Part.Line)
#------------------------------------------------------------------------------
def getObjectFaceFromName( obj, faceName ):
    assert faceName.startswith('Face')
    ind = int( faceName[4:]) -1 
    return obj.Shape.Faces[ind]
#------------------------------------------------------------------------------
def getProjectFolder():
    '''
    #------------------------------------------------------------------------------------
    # A new Parameter is required: projectFolder...
    # All Parts will be searched below this projectFolder-Value...        
    #------------------------------------------------------------------------------------
    '''
    if not USE_PROJECTFILE: return ""
    
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Assembly2")
    return preferences.GetString('projectFolder', '/Error=FirstSetPreferences/')

#------------------------------------------------------------------------------
def findSourceFileInProject(fullPath):
    ''' 
    #------------------------------------------------------------------------------------
    # function to find filename in projectFolder
    # The path stored in an imported Part will be ignored
    # Assemblies will become better movable in filesystem...
    #------------------------------------------------------------------------------------
    '''
    if not USE_PROJECTFILE: return fullPath

    def findFile(name, path):
        for root, dirs, files in os.walk(path):
            if name in files:
                return os.path.join(root, name) 
        
    projectFolder = getProjectFolder().rstrip('/')
    idx = fullPath.rfind('/')
    if idx >= 0:
        fileName = fullPath[idx+1:]
    else:
        fileName = fullPath
    return findFile(fileName,projectFolder)

#------------------------------------------------------------------------------
def checkFileIsInProjectFolder(path):
    if not USE_PROJECTFILE: return True

    nameInProject = findSourceFileInProject(path)
    if nameInProject == path:
        return True
    else:
        return False

#------------------------------------------------------------------------------
def pathOfModule():
    return os.path.dirname(__file__)

#------------------------------------------------------------------------------
def Msg(tx):
    FreeCAD.Console.PrintMessage(tx)
    
#------------------------------------------------------------------------------
def DebugMsg(tx):
    if DEBUGPROGRAM:
        FreeCAD.Console.PrintMessage(tx)

#------------------------------------------------------------------------------
def drawVector(fromPoint,toPoint, color): 
    if fromPoint == toPoint: return
    doc = FreeCAD.ActiveDocument
    
    l = Part.Line(fromPoint,toPoint)
    line = doc.addObject("Part::Feature","ArrowTail")
    line.Shape = l.toShape()
    line.ViewObject.LineColor = color
    line.ViewObject.LineWidth = 6
    #doc.recompute()
    c = Part.makeCone(0,1,4)
    cone = doc.addObject("Part::Feature","ArrowHead")
    cone.Shape = c
    cone.ViewObject.ShapeColor = (1.0,0.0,0.0)
    #
    mov = Base.Vector(0,0,0)
    zAxis = Base.Vector(0,0,-1)
    rot = FreeCAD.Rotation(zAxis,toPoint.sub(fromPoint))
    cent = Base.Vector(0,0,0)
    conePlacement = FreeCAD.Placement(mov,rot,cent)
    cone.Placement = conePlacement.multiply(cone.Placement)
    cone.Placement.move(toPoint) 
    doc.recompute()
    
#------------------------------------------------------------------------------
def findUnusedObjectName(base, counterStart=1, fmt='%03i', document=None):
    if document == None:
        document = FreeCAD.ActiveDocument
    i = counterStart
    usedNames = [ obj.Name for obj in document.Objects ]    
    
    if base[-4:-3] == '_':
        base2 = base[:-4]
    else:
        base2 = base
    base2 = base2 + '_'

    objName = '%s%s' % (base2, fmt%i)
    while objName in usedNames:
        i += 1
        objName = '%s%s' % (base2, fmt%i)
    return objName

#------------------------------------------------------------------------------
def findUnusedObjectLabel(base, counterStart=1, fmt='%03i', document=None):
    if document == None:
        document = FreeCAD.ActiveDocument
    i = counterStart
    usedLabels = [ obj.Label for obj in document.Objects ]    
    
    if base[-4:-3] == '_':
        base2 = base[:-4]
    else:
        base2 = base
    base2 = base2 + '_'

    objLabel = '%s%s' % (base2, fmt%i)
    while objLabel in usedLabels:
        i += 1
        objLabel = '%s%s' % (base2, fmt%i)
    return objLabel

#------------------------------------------------------------------------------
class ConstraintSelectionObserver:
    
    def __init__(self, selectionGate, parseSelectionFunction, 
                  taskDialog_title, taskDialog_iconPath, taskDialog_text,
                  secondSelectionGate=None):
        self.selections = []
        self.parseSelectionFunction = parseSelectionFunction
        self.secondSelectionGate = secondSelectionGate
        FreeCADGui.Selection.addObserver(self)  
        FreeCADGui.Selection.removeSelectionGate()
        FreeCADGui.Selection.addSelectionGate( selectionGate )
        wb_globals['selectionObserver'] = self
        self.taskDialog = SelectionTaskDialog(taskDialog_title, taskDialog_iconPath, taskDialog_text)
        FreeCADGui.Control.showDialog( self.taskDialog )
        
    def addSelection( self, docName, objName, sub, pnt ):
        obj = FreeCAD.ActiveDocument.getObject(objName)
        self.selections.append( SelectionRecord( docName, objName, sub ))
        if len(self.selections) == 2:
            self.stopSelectionObservation()
            self.parseSelectionFunction( self.selections)
        elif self.secondSelectionGate <> None and len(self.selections) == 1:
            FreeCADGui.Selection.removeSelectionGate()
            FreeCADGui.Selection.addSelectionGate( self.secondSelectionGate )
            
    def stopSelectionObservation(self):
        FreeCADGui.Selection.removeObserver(self) 
        del wb_globals['selectionObserver']
        FreeCADGui.Selection.removeSelectionGate()
        FreeCADGui.Control.closeDialog()
        
#------------------------------------------------------------------------------
class SelectionRecord:
    def __init__(self, docName, objName, sub):
        self.Document = FreeCAD.getDocument(docName)
        self.ObjectName = objName
        self.Object = self.Document.getObject(objName)
        self.SubElementNames = [sub]
        
#------------------------------------------------------------------------------
class SelectionTaskDialog:
    
    def __init__(self, title, iconPath, textLines ):
        self.form = SelectionTaskDialogForm( textLines )
        self.form.setWindowTitle( title )    
        if iconPath <> None:
            self.form.setWindowIcon( QtGui.QIcon( iconPath ) )
            
    def reject(self):
        wb_globals['selectionObserver'].stopSelectionObservation()

    def getStandardButtons(self): #http://forum.freecadweb.org/viewtopic.php?f=10&t=11801
        return 0x00400000 #cancel button
#------------------------------------------------------------------------------
class SelectionTaskDialogForm(QtGui.QWidget):    
    
    def __init__(self, textLines ):
        super(SelectionTaskDialogForm, self).__init__()
        self.textLines = textLines 
        self.initUI()
    
    def initUI(self):
        vbox = QtGui.QVBoxLayout()
        for line in self.textLines.split('\n'):
            vbox.addWidget( QtGui.QLabel(line) )
        self.setLayout(vbox)
        
#------------------------------------------------------------------------------
class SelectionExObject:
    'allows for selection gate funtions to interface with classification functions below'
    def __init__(self, doc, Object, subElementName):
        self.doc = doc
        self.Object = Object
        self.ObjectName = Object.Name
        self.SubElementNames = [subElementName]
#------------------------------------------------------------------------------
def getObjectEdgeFromName( obj, name ):
    assert name.startswith('Edge')
    ind = int( name[4:]) -1 
    return obj.Shape.Edges[ind]
#------------------------------------------------------------------------------
def CircularEdgeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Edge'):
            edge = getObjectEdgeFromName( selection.Object, subElement)
            if not hasattr(edge, 'Curve'): #issue 39
                return False
            if hasattr( edge.Curve, 'Radius' ):
                return True
    return False
#------------------------------------------------------------------------------
def AxisOfPlaneSelected( selection ): #adding Planes/Faces selection for Axial constraints
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            if str(face.Surface) == '<Plane object>':
                return True
    return False
#------------------------------------------------------------------------------
def printSelection(selection):
    entries = []
    for s in selection:
        for e in s.SubElementNames:
            entries.append(' - %s:%s' % (s.ObjectName, e))
            if e.startswith('Face'):
                ind = int( e[4:]) -1 
                face = s.Object.Shape.Faces[ind]
                entries[-1] = entries[-1] + ' %s' % str(face.Surface)
    return '\n'.join( entries[:5] )
#------------------------------------------------------------------------------
def updateObjectProperties( c ):
    return
    '''
    if c.Type == 'axial' or c.Type == 'circularEdge':
        if not hasattr(c, 'lockRotation'):
            c.addProperty("App::PropertyBool","lockRotation","ConstraintInfo")
    '''
#------------------------------------------------------------------------------
def planeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            if str(face.Surface) == '<Plane object>':
                return True
    return False
#------------------------------------------------------------------------------
def vertexSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        return selection.SubElementNames[0].startswith('Vertex')
    return False
#------------------------------------------------------------------------------
def cylindricalPlaneSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            if hasattr(face.Surface,'Radius'):
                return True
            elif str(face.Surface).startswith('<SurfaceOfRevolution'):
                return True
    return False
#------------------------------------------------------------------------------
def LinearEdgeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Edge'):
            edge = getObjectEdgeFromName( selection.Object, subElement)
            if not hasattr(edge, 'Curve'): #issue 39
                return False
            if isLine(edge.Curve):
                return True
    return False
#------------------------------------------------------------------------------
def sphericalSurfaceSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            return str( face.Surface ).startswith('Sphere ')
    return False
#------------------------------------------------------------------------------
def getObjectVertexFromName( obj, name ):
    assert name.startswith('Vertex')
    ind = int( name[6:]) -1 
    return obj.Shape.Vertexes[ind]
#------------------------------------------------------------------------------
def removeConstraint( constraint ):
    'required as constraint.Proxy.onDelete only called when deleted through GUI'
    doc = constraint.Document
    if constraint.ViewObject != None: #do not this check is actually nessary ...
        constraint.ViewObject.Proxy.onDelete( constraint.ViewObject, None )
    doc.removeObject( constraint.Name )
#------------------------------------------------------------------------------


































    




















        