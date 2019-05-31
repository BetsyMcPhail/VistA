#!/usr/bin/env python

# A Python model to represent the relationship between packages/globals/_routines
#------------------------------------------------------------------------------
# Copyright 2011 The Open Source Electronic Health Record Agent
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#----------------------------------------------------------------

import json

from LogManager import logger
from UtilityFunctions import PACKAGE_COMPONENT_MAP

NOT_KILLED_EXPLICITLY_VALUE = ">>"
MUMPS_ROUTINE_PREFIX = "Mumps"

LINE_OFFSET_DELIM = ","

#==============================================================================
# A Class to represent the variable in a _calledRoutine
#==============================================================================
class AbstractVariable:
    def __init__(self, name, prefix, lineOffsets):
        self._name = name
        self._prefix = prefix
        self._lineOffsets = lineOffsets.split(LINE_OFFSET_DELIM)

    def getName(self):
        return self._name

    def appendLineOffsets(self, lineOffsets):
        self._lineOffsets.extend(lineOffsets)

    def getLineOffsets(self):
        return self._lineOffsets

    def getPrefix(self):
        return self._prefix

#==============================================================================
# Wrapper classes around the AbstractVariable, place holders
#==============================================================================
class LocalVariable(AbstractVariable):
    def __init__(self, name, prefix, cond):
        AbstractVariable.__init__(self, name, prefix, cond)

class GlobalVariable(AbstractVariable):
    def __init__(self, name, prefix, cond):
        AbstractVariable.__init__(self, name, prefix, cond)

class NakedGlobal(AbstractVariable):
    def __init__(self, name, prefix, cond):
        AbstractVariable.__init__(self, name, prefix, cond)

class MarkedItem(AbstractVariable):
    def __init__(self, name, prefix, cond):
        AbstractVariable.__init__(self, name, prefix, cond)

class LabelReference(AbstractVariable):
    def __init__(self, name, prefix, cond):
        AbstractVariable.__init__(self, name, prefix, cond)

#==============================================================================
#  A class to wrap up information about a VistA Routine
#==============================================================================
class Routine(object):
    def __init__(self, routineName, package=None):
        self._name = routineName
        self._localVariables = dict()
        self._globalVariables = dict()
        self._nakedGlobals = dict()
        self._markedItems = dict()
        self._labelReference = dict()
        self._entryPoints    = dict()
        self._interactionPoints = []
        self._calledRoutines = RoutineDepDict()
        self._callerRoutines = RoutineDepDict()
        self._refGlobals = dict()
        self._dbGlobals = dict()
        self._package = package
        self._comments = []
        self._originalName = routineName
        self._hasSourceCode = True
        self.structuredCode = []
        self._objType = "Routine"

    def getObjectType(self):
        return self._objType

    def setName(self, routineName):
        self._name = routineName

    def getName(self):
        return self._name

    def setOriginalName(self, originalName):
        self._originalName = originalName

    def getOriginalName(self):
        return self._originalName

    def addComment(self, comment):
        self._comments.append(comment)

    def getComment(self):
        return self._comments

    def addLocalVariables(self, localVar):
        varName = localVar.getName()
        if varName not in self._localVariables:
            self._localVariables[varName] = localVar
        else:
            self._localVariables[varName].appendLineOffsets(localVar.getLineOffsets())

    def getLocalVariables(self):
        return self._localVariables

    def addGlobalVariables(self, globalVariable):
        varName = globalVariable.getName()
        if varName not in self._globalVariables:
            self._globalVariables[varName] = globalVariable
        else:
            self._globalVariables[varName].appendLineOffsets(globalVariable.getLineOffsets())

    def getGlobalVariables(self):
        return self._globalVariables

    def addReferredGlobal(self, globalVar):
        if globalVar.getName() not in self._refGlobals:
            self._refGlobals[globalVar.getName()] = globalVar

    def getReferredGlobal(self):
        return self._refGlobals

    def addFilemanDbCallGlobal(self, dbGlobal, callTag=None):
        dbFileNo = dbGlobal.getFileNo() # if it is a file man file
        if not dbFileNo:
            return
        if dbFileNo not in self._dbGlobals:
            self._dbGlobals[dbFileNo] = (dbGlobal, [])
        self._dbGlobals[dbFileNo][1].append(callTag)
        dbGlobal.addFileManDbCallRoutine(self)

    def getFilemanDbCallGlobals(self):
        return self._dbGlobals

    def addNakedGlobals(self, nakedGlobal):
        varName = nakedGlobal.getName()
        if varName not in self._nakedGlobals:
            self._nakedGlobals[varName] = nakedGlobal
        else:
            self._nakedGlobals[varName].appendLineOffsets(nakedGlobal.getLineOffsets())

    def getNakedGlobals(self):
        return self._nakedGlobals

    def addMarkedItems(self, markedItem):
        varName = markedItem.getName()
        if varName not in self._markedItems:
            self._markedItems[varName] = markedItem
        else:
            self._markedItems[varName].appendLineOffsets(markedItem.getLineOffsets())

    def getMarkedItems(self):
        return self._markedItems

    def getLabelReferences(self):
        return self._labelReference

    def addLabelReference(self, labelReference):
        varName = labelReference.getName()
        if varName not in self._labelReference:
            self._labelReference[varName] = labelReference
        else:
            self._labelReference[varName].appendLineOffsets(labelReference.getLineOffsets())

    def getExternalReference(self):
        output = dict()
        for routineDict in self._calledRoutines.itervalues():
            for (routine, callTagDict) in routineDict.iteritems():
                routineName = routine.getName()
                for (callTag, lineOffsets) in callTagDict.iteritems():
                    output[(routineName, callTag)] = lineOffsets
        return output

    def getFilteredExternalReference(self, filterList=None):
        output = dict()
        if filterList:
          for routineDict in self._calledRoutines.itervalues():
              for (routine, callTagDict) in routineDict.iteritems():
                  if routine.getName() in filterList:
                      routineName = routine.getName()
                      for (callTag, lineOffsets) in callTagDict.iteritems():
                          output[(routineName, callTag)] = lineOffsets
                  else:
                      continue
        return output

    def addCallDepRoutines(self, depRoutine, callTag, lineOccurrences,
                           isCalled=True):
        if isCalled:
            depRoutines = self._calledRoutines
        else:
            depRoutines = self._callerRoutines
        package = depRoutine.getPackage()
        if package is None:
            logger.error("Routine does not have a package")
        if package not in depRoutines:
            depRoutines[package] = dict()
        if depRoutine not in depRoutines[package]:
            depRoutines[package][depRoutine] = dict()
        if callTag not in depRoutines[package][depRoutine]:
            depRoutines[package][depRoutine][callTag] = lineOccurrences.split(LINE_OFFSET_DELIM)
        else:
            depRoutines[package][depRoutine][callTag].extend(lineOccurrences.split(LINE_OFFSET_DELIM))

    def addCalledRoutines(self, routine, callTag, lineOccurrences):
        self.addCallDepRoutines(routine, callTag, lineOccurrences, True)
        routine.addCallerRoutines(self, callTag, lineOccurrences)

    def getCalledRoutines(self):
        return self._calledRoutines

    def __generateEntryList__(self, entries, totalEntries):
      """
        It removes the "$$" notation from entry points and
        removes any given paramters.
      """
      if type(entries) is list:
          totalEntries.append(entries[0].replace('$','').split('(',1))
      else:
          if '(' in entries:
              totalEntries.append(entries.replace('$','').split('(',1)[0])
          else:
              totalEntries.append(entries.replace('$',''))
      return totalEntries


    def __checkForICR__(self, entryPt, rtnJson):
      """
          Check all values within the entries of the JSON that are specific
          to the routine that match the current entry point
      """
      entryPtList=[]
      icrEntries=[]
      for icrEntry in rtnJson:
        if 'COMPONENT/ENTRY POINT' in icrEntry:
          for entry in icrEntry['COMPONENT/ENTRY POINT']:
            if 'COMPONENT/ENTRY POINT' in entry:
              entryPtList = self.__generateEntryList__(entry['COMPONENT/ENTRY POINT'],entryPtList)
              if entryPt in entryPtList:
                entryPtList.pop(entryPtList.index(entryPt))
                icrEntries.append(icrEntry)
      return icrEntries


    def addEntryPoint(self, entryPt, comm, icrJSON):
        """
            Add an EntryPoint value to a routine, after checking for ICR
            values
        """
        icrEntries=[]
        if entryPt not in self._entryPoints:
            if icrJSON:
                icrEntries = self.__checkForICR__(entryPt.split("(")[0], icrJSON)
            self._entryPoints[entryPt] = { "comments": comm, "icr": icrEntries}

    def getEntryPoints(self):
        return self._entryPoints

    def addInteractionEntry(self, interactionDict):
        self._interactionPoints.append(interactionDict)

    def getInteractionEntries(self):
        return self._interactionPoints

    def addCallerRoutines(self, depRoutine, callTag, lineOccurrences):
        self.addCallDepRoutines(depRoutine, callTag, lineOccurrences, False)

    def getCallerRoutines(self):
        return self._callerRoutines

    def setPackage(self, package):
        self._package = package

    def getPackage(self):
        return self._package

    def hasSourceCode(self):
        return self._hasSourceCode

    def setHasSourceCode(self, hasSourceCode):
        self._hasSourceCode = hasSourceCode

    #==========================================================================
    # operator
    #==========================================================================
    def __str__(self):
        return self._name
    def __repr__(self):
        return "Routine: %s" % self._name
    def __eq__(self, other):
        if not isinstance(other, Routine):
            return False
        return self._name == other._name
    def __lt__(self, other):
        if not isinstance(other, Routine):
            return False
        return self._name < other._name
    def __gt__(self, other):
        if not isinstance(other, Routine):
            return False
        return self._name > other._name
    def __le__(self, other):
        if not isinstance(other, Routine):
            return False
        return self._name <= other._name
    def __ge__(self, other):
        if not isinstance(other, Routine):
            return False
        return self._name >= other._name
    def __ne__(self, other):
        if not isinstance(other, Routine):
            return True
        return self._name != other._name
    def __hash__(self):
        return self._name.__hash__()

#==============================================================================
#
#==============================================================================
class PackageComponent(Routine):
  def __init__(self, name, number, package):
    Routine.__init__(self, name, package)
    self._name = name
    self._ien = number

  def __len__(self):
    return len(self.getName())

  def getIEN(self):
    return self._ien

  def getName(self):
    return self._name

  def setName(self,val):
    self._name = val

  def getObjectType(self):
    return self._objType

  def addObjectType(self,val):
    self._objType = val

#==============================================================================
#
#==============================================================================
class Function(Routine):
  def __init__(self,name,number,package):
    Routine.__init__(self,name,package)
    self._name = name
    self._ien = number

  def getIEN(self):
    return self._ien

  def getName(self):
    return self._name

  def setName(self,val):
    self._name = val

#==============================================================================
# class to represent a platform dependent generic _calledRoutine
#==============================================================================
class PlatformDependentGenericRoutine(Routine):
    def __init__(self, routineName, package):
        Routine.__init__(self, routineName, package)
        self._platformRoutines = dict()

    def getComment(self):
        return ""

    def addLocalVariables(self, localVar):
        pass

    def addNakedGlobals(self, nakedGlobals):
        pass

    def addMarkedItems(self, markedItem):
        pass

    def addCalledRoutines(self, routine, callTag, lineOccurrences):
        pass

    def hasSourceCode(self):
        return False

    def addPlatformRoutines(self, mappingList):
        for item in mappingList:
            if item[0] not in self._platformRoutines:
                self._platformRoutines[item[0]] = [Routine(item[0], self._package), item[1]]

    #
    def getPlatformDepRoutineInfoByName(self, routineName):
        """
            return a list of two elements, first is the Routine, second is the
            platform name
        """
        return self._platformRoutines.get(routineName, [None, None])

    def getAllPlatformDepRoutines(self):
        return self._platformRoutines

#==============================================================================
# # class to represent A FileMan File
#==============================================================================
class FileManFile(Routine):
    def __init__(self, fileNo, fileManName, parentFile=None):
        Routine.__init__(self, fileManName)
        self._fileNo = None
        self._fileManName = fileManName
        self._parentFile = parentFile
        self._fields = None # dict of all fields
        self._subFiles = None  # dict of all subFiles
        self._description = None # description of fileMan file
        self.setFileNo(fileNo)
        self._fileManDbCallRoutines = None
        self._fieldNames = []

    def getFileNo(self):
        return self._fileNo

    def getFieldNames(self):
        return self._fieldNames

    def setFileNo(self, fileNo):
        if fileNo:
            try:
                # Is fileNo a float?
                float(fileNo)
                self._fileNo = fileNo
            except ValueError:
                self._fileNo = None
        else:
            self._fileNo = None

    def getFileManName(self):
        return self._fileManName

    def addFileManField(self, fileManField):
        if not self._fields:
            self._fields = dict()
        if fileManField.getName() not in self._fieldNames:
            self._fieldNames.append(fileManField.getName())
        self._fields[fileManField.getFieldNo()] = fileManField

    def getAllFileManFields(self):
        return self._fields

    def hasField(self, fieldNo):
      return self._fields and fieldNo in self._fields

    def getField(self, fieldNo):
      if self._fields:
          return self._fields.get(fieldNo)
      return None

    def addFileManSubFile(self, fileManSubFile):
        if not self._subFiles:
            self._subFiles = dict()
        self._subFiles[fileManSubFile.getFileNo()] = fileManSubFile

    def getAllSubFiles(self):
        return self._subFiles

    def isRootFile(self):
        return self._parentFile is None

    def isSubFile(self):
        return not self.isRootFile()

    def getParentFile(self):
        return self._parentFile

    def setParentFile(self, parentFile):
        self._parentFile = parentFile

    def getRootFile(self):
        root = self
        while not root.isRootFile():
            root = root.getParentFile()
        return root

    def getSubFileByFileNo(self, fileNo):
        if not self._subFiles:
            return None
        return self._subFiles.get(fileNo)

    def getFileManFieldByFieldNo(self, fieldNo):
        if not self._fields:
            return None
        return self._fields.get(fieldNo)

    def getDescription(self):
        return self._description

    def setDescription(self, description):
        self._description = [x.decode('latin1').encode('utf8') for x in description]

    def getFileManDbCallRoutines(self):
        return self._fileManDbCallRoutines

    def addFileManDbCallRoutine(self, routine):
        if not routine:
            return
        package = routine.getPackage()
        if not package:
            return
        if not self._fileManDbCallRoutines:
            self._fileManDbCallRoutines = dict()
        if package not in self._fileManDbCallRoutines:
            self._fileManDbCallRoutines[package] = set()
        self._fileManDbCallRoutines[package].add(routine)

    #==========================================================================
    # operator
    #==========================================================================
    def __str__(self):
        return self._fileNo
    def __repr__(self):
        return "File: %s, Name: %s" % (self._fileNo, self._fileManName)

#==============================================================================
# # class to represent a Field in FileMan File
#==============================================================================
class FileManField(json.JSONEncoder):
    FIELD_TYPE_NONE = 0 # Field has No Type, normally just a place hold
    FIELD_TYPE_DATE_TIME = 1
    FIELD_TYPE_NUMBER = 2
    FIELD_TYPE_SET = 3
    FIELD_TYPE_FREE_TEXT = 4
    FIELD_TYPE_WORD_PROCESSING = 5
    FIELD_TYPE_COMPUTED = 6
    FIELD_TYPE_FILE_POINTER = 7
    FIELD_TYPE_VARIABLE_FILE_POINTER = 8
    FIELD_TYPE_SUBFILE_POINTER = 9
    FIELD_TYPE_MUMPS = 10
    FIELD_TYPE_BOOLEAN = 11
    FIELD_TYPE_LAST = 12

    # Enumeration for SPECIFIER
    FIELD_SPECIFIED_NONE = 0
    FIELD_SPECIFIER_REQUIRED = 1
    FIELD_SPECIFIER_AUDIT= 2
    FIELD_SPECIFIER_MULTILINE = 3
    FIELD_SPECIFIER_LAYGO_NOT_ALLOWED = 4
    FIELD_SPECIFIER_OUTPUT_TRANSFORM = 5
    FIELD_SPECIFIER_EDITING_NOT_ALLOWD = 6
    FIELD_SPECIFIER_NO_WORD_WRAPPING = 7
    FIELD_SPECIFIER_IGORE_PIPE = 8
    FIELD_SPECIFIER_NEW_ENTRY_NO_ASK = 9
    FIELD_SPECIFIER_MULTIPLE_ASKED = 10
    FIELD_SPECIFIER_UNEDITABLE = 11
    FIELD_SPECIFIER_AUDIT_EDIT_DELETE = 12
    FIELD_SPECIFIER_EDIT_PROG_ONLY = 13
    FIELD_SPECIFIER_POINTER_SCREEN = 14

    def __init__(self, fieldNo, name, fType ,location = None):
        self._fieldNo = None
        self.setFieldNo(fieldNo)
        self._name = name
        self._loc = location
        self._type = fType
        self._subType = None
        self._specifier = None
        self._typeName = None
        self._indexName = None
        self._propList = None # store extra information is name value pair format
        # attributes
        self._isRequired = False
        self._isAudited = False
        self._isAddNewEntryWithoutAsking = False
        self._isMultiplyAsked = False
        self._isKeyField = False

    def setFieldNo(self, fieldNo):
        if fieldNo:
            try:
                # Ensure that fileNo is a float
                float(fieldNo)
                self._fieldNo = fieldNo
            except ValueError:
                self._fieldNo = None
        else:
            self._fieldNo = None

    def getName(self):
        return self._name

    def getLocation(self):
        return self._loc

    def getType(self):
        return self._type

    def getSubType(self):
        return self._subType

    def addSubType(self, subType):
        if not self._subType:
           self._subType = []
        self._subType.append(subType)

    def hasSubType(self, subType):
        if self._subType:
            return subType in self._subType
        return False

    def getSpecifier(self):
        return self._specifier

    def setSpecifier(self, specifier):
        self._specifier = specifier

    def getFieldNo(self):
        return self._fieldNo

    def getTypeName(self):
        return self._typeName

    def setTypeName(self, typeName):
        self._typeName = typeName

    def addProp(self, propName, propValue):
        if not self._propList:
            self._propList = []
        self._propList.append((propName, propValue))

    def getPropList(self):
        return self._propList

    # type checking method
    def isFilePointerType(self):
        return self._type == self.FIELD_TYPE_FILE_POINTER

    def isSubFilePointerType(self):
        return self._type == self.FIELD_TYPE_SUBFILE_POINTER

    def isVariablePointerType(self):
        return self._type == self.FIELD_TYPE_VARIABLE_FILE_POINTER

    def isSetType(self):
        return self._type == self.FIELD_TYPE_SET
    #==========================================================================
    # operator
    #==========================================================================
    def __str__(self):
        return self._fieldNo
    def __repr__(self):
        return ("%s, %s, %s, %s, %s, %s, %s" % (self.getFieldNo(),
                                                self.getName(),
                                                self.getLocation(),
                                                self.getTypeName(),
                                                self.getType(),
                                                self.getSubType(),
                                                self.getSpecifier()))

#==============================================================================
# A series of subclass of FileManField based on type
#==============================================================================
class FileManNoneTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_NONE
        FileManField.__init__(self, fieldNo, name, fType ,location)

class FileManDateTimeTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_DATE_TIME
        FileManField.__init__(self, fieldNo, name, fType ,location)

class FileManNumberTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_NUMBER
        FileManField.__init__(self, fieldNo, name, fType ,location)

class FileManSetTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_SET
        FileManField.__init__(self, fieldNo, name, fType ,location)
        self._setMembers = []

    def getSetMembers(self):
        return self._setMembers

    def setSetMembers(self, memList):
        self._setMembers = memList

    def __repr__(self):
        return "%s, %s" % (FileManField.__repr__(self), self._setMembers)

class FileManFreeTextTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_FREE_TEXT
        FileManField.__init__(self, fieldNo, name, fType ,location)

class FileManWordProcessingTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_WORD_PROCESSING
        FileManField.__init__(self, fieldNo, name, fType ,location)
        self._isNoWrap = False
        self._ignorePipe = False

    def __repr__(self):
        return ("%s, %s, %s" % (FileManField.__repr__(self),
                                self._isNoWrap,
                                self._ignorePipe))

class FileManComputedTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_COMPUTED
        assert location == None
        FileManField.__init__(self, fieldNo, name, fType ,location)

class FileManFilePointerTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_FILE_POINTER
        FileManField.__init__(self, fieldNo, name, fType ,location)
        self._filePointedTo = None

    def setPointedToFile(self, filePointedTo):
        self._filePointedTo = filePointedTo

    def getPointedToFile(self):
        return self._filePointedTo

    def __repr__(self):
        return ("%s, %s" % (FileManField.__repr__(self),
                            self._filePointedTo))

class FileManVariablePointerTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_VARIABLE_FILE_POINTER
        FileManField.__init__(self, fieldNo, name, fType ,location)
        self._pointedToFiles = []

    def setPointedToFiles(self, pointedToFiles):
      if pointedToFiles:
        self._pointedToFiles = pointedToFiles
      else:
        self._pointedToFiles = []

    def getPointedToFiles(self):
        return self._pointedToFiles

    def __repr__(self):
        return "%s, %s" % (FileManField.__repr__(self), self._pointedToFiles)

class FileManSubFileTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_SUBFILE_POINTER
        FileManField.__init__(self, fieldNo, name, fType ,location)
        self._pointedToSubFile= None

    def setPointedToSubFile(self, pointedToSubFile):
        self._pointedToSubFile = pointedToSubFile

    def getPointedToSubFile(self):
        return self._pointedToSubFile

    def __repr__(self):
        return ("%s, %s" % (FileManField.__repr__(self),
                            self._pointedToSubFile))

class FileManMumpsTypeField(FileManField):
    def __init__(self, fieldNo, name, fType ,location = None):
        assert fType == self.FIELD_TYPE_MUMPS
        FileManField.__init__(self, fieldNo, name, fType ,location)

class FileManFieldFactory:
    _creationTuple_ = (FileManNoneTypeField, FileManDateTimeTypeField,
                       FileManNumberTypeField, FileManSetTypeField,
                       FileManFreeTextTypeField, FileManWordProcessingTypeField,
                       FileManComputedTypeField, FileManFilePointerTypeField,
                       FileManVariablePointerTypeField, FileManSubFileTypeField,
                       FileManMumpsTypeField)
    @staticmethod
    def createField(fieldNo, name, fType, location = None):
        assert (fType >= FileManField.FIELD_TYPE_NONE and
                fType < FileManField.FIELD_TYPE_LAST)
        if fType < len(FileManFieldFactory._creationTuple_):
            return FileManFieldFactory._creationTuple_[fType](fieldNo,
                                                              name,
                                                              fType,
                                                              location)
        else:
            return FileManField(fieldNo, name, fType, location)

#==============================================================================
# # class to represent a global variable inherits FileManFile
#==============================================================================
class Global(FileManFile):
    def __init__(self, globalName,
                 fileNo=None,
                 fileManName = None,
                 package=None):
        FileManFile.__init__(self, fileNo, fileManName)
        self._name = globalName
        self._package = package
        self._referencesRoutines = dict() # accessed by routines directly
        self._filePointers = dict() # pointer to some other file
        self._filePointedBy = dict() # pointed to by some other files
        self._totalReferencedRoutines = 0
        self._totalReferencedGlobals = 0
        self._totalReferredGlobals = 0
        self._objType = "Global"

    def setName(self, globalName):
        self._name = globalName

    def getName(self):
        return self._name

    def getTotalNumberOfReferencedRoutines(self):
        return self._totalReferencedRoutines

    def getAllReferencedRoutines(self):
        return self._referencesRoutines

    def getTotalNumberOfReferencedGlobals(self):
        return self._totalReferencedGlobals

    def getAllReferencedFileManFiles(self):
        return self._filePointedBy

    def getTotalNumberOfReferredGlobals(self):
        return self._totalReferredGlobals

    def getAllReferredFileManFiles(self):
        return self._filePointers

    def hasPointerToFileManFile(self, fileManFile, fileManFieldNo, subFileNo):
        return self.__hasFileManFileDependency__(fileManFile, fileManFieldNo,
                                                 subFileNo, False)

    def isPointedToByFileManFile(self, fileManFile, fileManFieldNo, subFileNo):
        return self.__hasFileManFileDependency__(fileManFile, fileManFieldNo,
                                                 subFileNo, True)

    def __hasFileManFileDependency__(self, fileManFile, fileManFieldNo,
                                     subFileNo, isPointedToBy=True):
        assert isinstance(fileManFile, Global),  "Must be a Global instance, [%s]" % fileManFile
        package = fileManFile.getPackage()
        if not package:
            return False
        filePointerDeps = self._filePointedBy
        if not isPointedToBy:
            filePointerDeps = self._filePointers
        if package not in filePointerDeps:
            return False
        if fileManFile in filePointerDeps[package]:
            return (fileManFieldNo, subFileNo) in filePointerDeps[package][fileManFile]
        return False

    def addReferencedRoutine(self, routine):
        if not routine:
            return
        package = routine.getPackage()
        if not package:
            return
        if package not in self._referencesRoutines:
            self._referencesRoutines[package] = set()
        self._referencesRoutines[package].add(routine)
        self._totalReferencedRoutines = self._totalReferencedRoutines + 1

    def addPointedToByFile(self, Global, fieldNo, subFileNo=None):
        self.__addReferenceGlobalFilesCommon__(Global, fieldNo, subFileNo,
                                               pointedToBy=True)
        Global.__addPointedToFiles__(self, fieldNo, subFileNo)

    def __addPointedToFiles__(self, Global, fieldNo, subFileNo):
        self.__addReferenceGlobalFilesCommon__(Global, fieldNo, subFileNo,
                                               pointedToBy=False)

    def __addReferenceGlobalFilesCommon__(self, Global, fieldNo, subFileNo,
                                          pointedToBy=True):
        if not Global:
            return
        package = Global.getPackage()
        if not package:
            return
        depFileDict = self._filePointedBy
        if not pointedToBy:
            depFileDict = self._filePointers
        if package not in depFileDict:
            depFileDict[package] = dict()
        if Global not in depFileDict[package]:
            depFileDict[package][Global] = []
            if pointedToBy:
                self._totalReferredGlobals = self._totalReferredGlobals + 1
                Global._totalReferencedGlobals = Global._totalReferencedGlobals + 1
        depFileDict[package][Global].append((fieldNo, subFileNo))

    def setPackage(self, package):
        self._package = package

    def isFileManFile(self):
        return self.getFileNo() != None

    def getPackage(self):
        return self._package

    def getObjectType(self):
        return self._objType

    #==========================================================================
    # operator
    #==========================================================================
    def __str__(self):
        return self._name
    def __repr__(self):
        return "Global: %s" % self._name
    def __eq__(self, other):
        if not isinstance(other, Global):
            return False
        return self._name == other._name
    def __lt__(self, other):
        if not isinstance(other, Global):
            return False
        return self._name < other._name
    def __gt__(self, other):
        if not isinstance(other, Global):
            return False
        return self._name > other._name
    def __le__(self, other):
        if not isinstance(other, Global):
            return False
        return self._name <= other._name
    def __ge__(self, other):
        if not isinstance(other, Global):
            return False
        return self._name >= other._name
    def __ne__(self, other):
        if not isinstance(other, Global):
            return True
        return self._name != other._name
    def __hash__(self):
        return self._name.__hash__()

#==============================================================================
# # Utilities function related to Global
#==============================================================================
def getAlternateGlobalName(globalName):
    pos = globalName.find("(") # this should find the very first "("
    if pos == -1:
        return globalName + "("
    if pos == len(globalName) - 1:
        return globalName[0:len(globalName)-1]
    return globalName

def getTopLevelGlobalName(globalName):
    pos = globalName.find("(") # this should find the very first "("
    if pos == -1: # could not find, must be the top level name already
        return globalName[1:]
    return globalName[1:pos]

#==============================================================================
# class to represent a VistA Package
#==============================================================================
class Package(object):
    #constructor
    def __init__(self, packageName):
        self._name = packageName
        self._routines = dict()
        self._globals = dict()
        self._namespaces = []
        self._objects = dict()
        for componentType in PACKAGE_COMPONENT_MAP:
            self._objects[componentType] = dict()
        self._globalNamespace = []
        self._routineDependencies = dict()
        self._routineDependents = dict()
        self._globalRoutineDependencies = dict()
        self._globalRoutineDependendents = dict()
        self._objectDependencies = dict()
        self._objectDependents = dict()
        self._globalDependencies = dict()
        self._globalGlobalDependencies = dict()
        self._globalGlobalDependendents = dict()
        self._globalDependents = dict()
        self._fileManDependencies = dict()
        self._fileManDependents = dict()
        # fileman db call related dependencies
        self._fileManDbDependencies = dict()
        self._fileManDbDependents = dict()
        self._origName = packageName
        self._docLink = ""
        self._docMirrorLink = ""
        self.rpcs = []
        self.hl7 = []
        self.protocol = []
        self.hlo = []

    def addRoutine(self, routine):
        self._routines[routine.getName()] = routine
        routine.setPackage(self)

    def addGlobal(self, globalVar):
        self._globals[globalVar.getName()] = globalVar
        globalVar.setPackage(self)

    def getAllRoutines(self):
        return self._routines

    def getAllGlobals(self):
        return self._globals

    #**************************************
    #* Package object functions
    #**************************************
    def getPackageComponent(self, type, ien):
        return self._objects[type][ien]

    def getAllPackageComponents(self, type="*"):
      if type == "*":
          return self._objects
      return self._objects[type]

    def addPackageComponent(self, type, value):
        value.addObjectType(type)
        self._objects[type][value.getIEN()] = value

    def hasRoutine(self, routineName):
        return routineName in self._routines

    def getName(self):
        return self._name

    def getOriginalName(self):
        return self._origName

    def setOriginalName(self, origName):
        self._origName = origName

    def generatePackageDependencies(self):
        self.generatePackageComponentBasedDependencies()
        self.generateRoutineBasedDependencies()
        self.generateFileManFileBasedDependencies()

    def generatePackageComponentBasedDependencies(self):
        allObjs = self.getAllPackageComponents()
        for key in allObjs:
            for obj in allObjs[key]:
                calledRoutines = allObjs[key][obj].getCalledRoutines()
                for package in calledRoutines.iterkeys():
                    if package and package != self:
                        if package not in self._objectDependencies:
                            # the first set consists of all caller
                            # _calledRoutine in the self package
                            # the second set consists of all called routines
                            # in dependency package
                            self._objectDependencies[package] = (set(), set())
                        self._objectDependencies[package][0].add(allObjs[key][obj])
                        self._objectDependencies[package][1].update(calledRoutines[package])
                        if self not in package._objectDependents:
                            # the first set consists of all called
                            # _calledRoutine in the package
                            # the second set consists of all caller routines
                            # in that package
                            package._objectDependents[self] = (set(), set())
                        package._objectDependents[self][0].add(allObjs[key][obj])
                        package._objectDependents[self][1].update(calledRoutines[package])

    def generateRoutineBasedDependencies(self):
        # build routine based dependencies
        for globalEntry in self._globals.itervalues():
            calledRoutines =  globalEntry.getCalledRoutines()
            for package in calledRoutines.iterkeys():
                if package and package != self:
                    if package not in self._globalRoutineDependencies:
                        # the first set consists of all caller
                        # _calledRoutine in the self package
                        # the second set consists of all called routines in
                        # dependency package
                        self._globalRoutineDependencies[package] = (set(), set())
                    self._globalRoutineDependencies[package][0].add(globalEntry)
                    self._globalRoutineDependencies[package][1].update(calledRoutines[package])
                    if self not in package._globalRoutineDependendents:
                        # the first set consists of all called
                        # _calledRoutine in the package
                        # the second set consists of all caller routines in
                        # that package
                        package._globalRoutineDependendents[self] = (set(), set())
                    package._globalRoutineDependendents[self][0].add(globalEntry)
                    package._globalRoutineDependendents[self][1].update(calledRoutines[package])
            referredGlobals = globalEntry.getReferredGlobal()
            for globalVar in referredGlobals.itervalues():
                package = globalVar.getPackage()
                if package != self:
                    if package not in self._globalGlobalDependencies:
                        self._globalGlobalDependencies[package] = (set(), set())
                    self._globalGlobalDependencies[package][0].add(globalEntry)
                    self._globalGlobalDependencies[package][1].add(globalVar)
                    if self not in package._globalGlobalDependendents:
                        package._globalGlobalDependendents[self] = (set(), set())
                    package._globalGlobalDependendents[self][0].add(globalEntry)
                    package._globalGlobalDependendents[self][1].add(globalVar)
        for routine in self._routines.itervalues():
            calledRoutines = routine.getCalledRoutines()
            for package in calledRoutines.iterkeys():
                if package and package != self:
                    if package not in self._routineDependencies:
                        # the first set consists of all caller _calledRoutine in the self package
                        # the second set consists of all called routines in dependency package
                        self._routineDependencies[package] = (set(), set())
                    self._routineDependencies[package][0].add(routine)
                    self._routineDependencies[package][1].update(calledRoutines[package])
                    if self not in package._routineDependents:
                        # the first set consists of all called # _calledRoutine in the package
                        # the second set consists of all caller routines in # that package
                        package._routineDependents[self] = (set(), set())
                    package._routineDependents[self][0].add(routine)
                    package._routineDependents[self][1].update(calledRoutines[package])
            referredGlobals = routine.getReferredGlobal()
            # based on referred Globals
            for globalVar in referredGlobals.itervalues():
                package = globalVar.getPackage()
                if package != self:
                    if package not in self._globalDependencies:
                        self._globalDependencies[package] = (set(), set())
                    self._globalDependencies[package][0].add(routine)
                    self._globalDependencies[package][1].add(globalVar)
                    if self not in package._globalDependents:
                        package._globalDependents[self] = (set(), set())
                    package._globalDependents[self][0].add(routine)
                    package._globalDependents[self][1].add(globalVar)
            # based on fileman db calls
            filemanDbCallGbls = routine.getFilemanDbCallGlobals()
            for filemanDbGbl in filemanDbCallGbls:
                # find the package associated with the global
                package = filemanDbGbl.getRootFile().getPackage()
                if package != self:
                    if package not in self._fileManDbDependencies:
                        self._fileManDbDependencies[package] = (set(), set())
                    self._fileManDbDependencies[package][0].add(routine)
                    self._fileManDbDependencies[package][1].add(filemanDbGbl)
                    if self not in package._fileManDbDependents:
                        package._fileManDbDependents[self] = (set(), set())
                    package._fileManDbDependents[self][0].add(routine)
                    package._fileManDbDependents[self][1].add(filemanDbGbl)

    def generateFileManFileBasedDependencies(self):
        # build fileman file based dependencies
        self.__correctFileManFilePointerDependencies__()
        for Global in self._globals.itervalues():
            if not Global.isFileManFile():
                # only care about the file man file now
                continue
            pointerToFiles = Global.getAllReferredFileManFiles()
            for package in pointerToFiles.iterkeys():
                if package != self:
                    if package not in self._fileManDependencies:
                        self._fileManDependencies[package] = (set(), set())
                    self._fileManDependencies[package][0].add(Global)
                    self._fileManDependencies[package][1].update(pointerToFiles[package])
                    if self not in package._fileManDependents:
                        package._fileManDependents[self] = (set(), set())
                    package._fileManDependents[self][0].add(Global)
                    package._fileManDependents[self][1].update(pointerToFiles[package])

    # this routine will correct any inconsistence caused by parsing logic
    def __correctFileManFilePointerDependencies__(self):
        for Global in self._globals.itervalues():
            if not Global.isFileManFile():
                # only care about the file man file now
                continue
            self.__checkIndividualFileManPointers__(Global)

    def __checkIndividualFileManPointers__(self, Global, subFile=None):
        currentGlobal = Global
        if subFile:
            currentGlobal = subFile
        allFileManFields = currentGlobal.getAllFileManFields()
        # get all fields of the current global
        if allFileManFields:
            for field in allFileManFields.itervalues():
                if field.isFilePointerType():
                    fileManFile = field.getPointedToFile()
                    self.__checkFileManPointerField__(field, fileManFile,
                                                      Global, subFile)
                    continue
                if field.isVariablePointerType():
                    fileManFiles = field.getPointedToFiles()
                    for fileManFile in fileManFiles:
                        self.__checkFileManPointerField__(field, fileManFile,
                                                          Global, subFile)
                    continue
        if not subFile:
            # get all subfiles of current globals
            allSubFiles = Global.getAllSubFiles()
            if not allSubFiles:
                return
            for subFile in allSubFiles.itervalues():
                self.__checkIndividualFileManPointers__(Global, subFile)

    def __checkFileManPointerField__(self, field, fileManFile, Global,
                                     subFile=None):
        if not fileManFile:
            logger.warning("Invalid fileMan File pointed to by field:[%s], Global:[%s], subFile:[%s]" % (field, Global, subFile))
            return
        # make sure that fileManFile is in the Global' filePointers
        fieldNo = field.getFieldNo()
        subFileNo = None
        if subFile:
            subFileNo = subFile.getFileNo()
        if not Global.hasPointerToFileManFile(fileManFile, fieldNo, subFileNo):
            logger.warning("Global[%r] does not have a pointer to [%r] at [%s]:[%s]" % (Global, fileManFile, fieldNo, subFileNo))
            fileManFile.addPointedToByFile(Global, fieldNo, subFileNo)
            return
        if not fileManFile.isPointedToByFileManFile(Global, fieldNo, subFileNo):
            logger.warning("FileMan file[%r] does not pointed to by [%r] at [%s]:[%s]" % (fileManFile, Global, fieldNo, subFileNo))
            fileManFile.addPointedToByFile(Global, fieldNo, subFileNo)
            return

    def getPackageComponentDependencies(self):
        return self._objectDependencies

    def getPackageRoutineDependencies(self):
        return self._routineDependencies

    def getPackageGlobalRoutineDependencies(self):
        return self._globalRoutineDependencies

    def getPackageGlobalRoutineDependendents(self):
        return self._globalRoutineDependendents

    def getPackageRoutineDependents(self):
        return self._routineDependents

    def getPackageGlobalDependencies(self):
        return self._globalDependencies

    def getPackageGlobalDependents(self):
        return self._globalDependents

    def getPackageGlobalGlobalDependencies(self):
        return self._globalGlobalDependencies

    def getPackageGlobalGlobalDependents(self):
        return self._globalGlobalDependendents

    def getPackageFileManFileDependencies(self):
        return self._fileManDependencies

    def getPackageFileManFileDependents(self):
        return self._fileManDependents

    def getPackageFileManDbCallDependencies(self):
        return self._fileManDbDependencies

    def getPackageFileManDbCallDependents(self):
        return self._fileManDbDependents

    def addNamespace(self, namespace):
        self._namespaces.append(namespace)

    def getNamespaces(self):
        return self._namespaces

    def addGlobalNamespace(self, namespace):
        self._globalNamespace.append(namespace)

    def getGlobalNamespace(self):
        return self._globalNamespace

    def getDocLink(self):
        return self._docLink

    def getDocMirrorLink(self):
        return self._docMirrorLink

    def setDocLink(self, docLink):
        self._docLink = docLink

    #===========================================================================
    # operator
    #===========================================================================
    def __str__(self):
        return self._name
    def __repr__(self):
        return "Package: %s" % self._name
    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        return self._name == other._name
    def __lt__(self, other):
        if not isinstance(other, Package):
            return False
        return self._name < other._name
    def __gt__(self, other):
        if not isinstance(other, Package):
            return False
        return self._name > other._name
    def __le__(self, other):
        if not isinstance(other, Package):
            return False
        return self._name <= other._name
    def __ge__(self, other):
        if not isinstance(other, Package):
            return False
        return self._name >= other._name
    def __ne__(self, other):
        if not isinstance(other, Package):
            return True
        return self._name != other._name
    def __hash__(self):
        return self._name.__hash__()

#===============================================================================
# A Class represent all called/caller _calledRoutine Dictionary
#===============================================================================
class RoutineDepDict(dict):
    '''
    placeholder
    '''

#===============================================================================
# A Wrapper class represents all Cross Reference Information
#===============================================================================
class CrossReference:
    def __init__(self):
        self._allPackages = dict()
        self._allRoutines = dict()
        self._orphanRoutines = set()
        self._allGlobals = dict()
        self._allFileManGlobals = dict() # Globals that are managed by FileMan
        self._orphanGlobals = set()
        self._percentRoutine = set()
        self._percentRoutineMapping = dict()
        self._renameRoutines = dict()
        self._mumpsRoutines = set()
        self._platformDepRoutines = dict() # [name, package, mapping list]
        self._platformDepRoutineMappings = dict() # [platform dep _calledRoutine -> generic _calledRoutine]
        self._allFileManSubFiles = dict() # store all fileman subfiles

    def getAllRoutines(self):
        return self._allRoutines

    def getAllPackages(self):
        return self._allPackages

    def getAllGlobals(self):
        return self._allGlobals

    def getAllFileManSubFiles(self):
        return self._allFileManSubFiles

    def hasPackage(self, packageName):
        return packageName in self._allPackages

    def hasRoutine(self, routineName):
        return routineName in self._allRoutines

    def hasGlobal(self, globalName):
        return globalName in self._allGlobals

    def addPackageByName(self, packageName):
        if not self.hasPackage(packageName):
            self._allPackages[packageName] = Package(packageName)

    def getRoutineByName(self, routineName):
        newRtnName = routineName
        if self.routineNeedRename(routineName):
            newRtnName = self.getRenamedRoutineName(routineName)
        if self.isPlatformDependentRoutineByName(newRtnName):
            return self.getPlatformDependentRoutineByName(newRtnName)
        return self._allRoutines.get(newRtnName)

    def getPackageByName(self, packageName):
        return self._allPackages.get(packageName)

    def getGlobalByName(self, globalName):
        return self._allGlobals.get(globalName)

    def getGlobalByFileNo(self, globalFileNo):
        return self._allFileManGlobals.get(float(globalFileNo))

    def addRoutineToPackageByName(self, routineName, packageName,
                                  hasSourceCode=True):
        if packageName not in self._allPackages:
            self._allPackages[packageName] = Package(packageName)
        if routineName not in self._allRoutines:
            self._allRoutines[routineName] = Routine(routineName)
        routine = self._allRoutines[routineName]
        if not hasSourceCode:
            routine.setHasSourceCode(hasSourceCode)
        self._allPackages[packageName].addRoutine(routine)

    def addNonFileManGlobalByName(self, globalName):
        if self.getGlobalByName(globalName):
            return None # already exists
        topLevelName = getTopLevelGlobalName(globalName)
        (namespace, package) = self.categorizeGlobalByNamespace(topLevelName)
        if not package:
            package = self.getPackageByName("Uncategorized")
            self.addToOrphanGlobalByName(globalName)
        globalVar = Global(globalName, None, None, package)
        self.addGlobalToPackage(globalVar, package.getName())
        return globalVar

    def addGlobalToPackage(self, globalVar, packageName):
        if packageName not in self._allPackages:
            self._allPackages[packageName] = Package(packageName)
        if globalVar.getName() not in self._allGlobals:
            self._allGlobals[globalVar.getName()] = globalVar
        self._allPackages[packageName].addGlobal(self._allGlobals[globalVar.getName()])
        # also added to fileMan Globals
        fileNo = globalVar.getFileNo()
        if fileNo:
            realFileNo = float(fileNo)
            if realFileNo not in self._allFileManGlobals:
                self._allFileManGlobals[realFileNo] = self._allGlobals[globalVar.getName()]

    def addFileManSubFile(self, subFile):
        self._allFileManSubFiles[subFile.getFileNo()] = subFile

    def isFileManSubFileByFileNo(self, subFileNo):
        return subFileNo in self._allFileManSubFiles

    def getFileManSubFileByFileNo(self, subFileNo):
        return self._allFileManSubFiles.get(subFileNo)

    def getSubFileRootByFileNo(self, subFileNo):
        root = self.getFileManSubFileByFileNo(subFileNo)
        if not root:
            return None
        return root.getRootFile()

    def addToOrphanGlobalByName(self, globalName):
        if not self.hasGlobal(globalName):
            self._orphanGlobals.add(globalName)

    def addPercentRoutine(self, routineName):
        self._percentRoutine.add(routineName)

    # this should be called after we have all the call graph information
    def addPercentRoutineMapping(self, routineName, mappingRoutineName,
                                 mappingPackage):
        if routineName not in self._percentRoutineMapping:
            self._percentRoutineMapping[routineName] = []
        self._percentRoutineMapping[routineName].append(mappingRoutineName)
        self._percentRoutineMapping[routineName].append(mappingPackage)
        if mappingRoutineName:
            self._renameRoutines[mappingRoutineName] = routineName
        elif mappingPackage.startswith(MUMPS_ROUTINE_PREFIX):
            self._mumpsRoutines.add(routineName)

    def routineNeedRename(self, routineName):
        return routineName in self._renameRoutines

    def getRenamedRoutineName(self, routineName):
        return self._renameRoutines.get(routineName)

    def isMumpsRoutine(self, routineName):
        return routineName in self._mumpsRoutines

    def addPlatformDependentRoutineMapping(self, routineName,
                                           packageName,
                                           mappingList):
        if routineName not in self._platformDepRoutines:
            routine = PlatformDependentGenericRoutine(routineName,
                                                      self.getPackageByName(packageName))
            self._platformDepRoutines[routineName] = routine
        routine = self._platformDepRoutines[routineName]
        routine.addPlatformRoutines(mappingList)
        self._allRoutines[routineName] = routine
        self._allPackages[packageName].addRoutine(routine)
        for item in mappingList:
            self._platformDepRoutineMappings[item[0]] = routineName

    def isPlatformDependentRoutineByName(self, routineName):
        return routineName in self._platformDepRoutineMappings

    def isPlatformGenericRoutineByName(self, routineName):
        return routineName in self._platformDepRoutines

    def getGenericPlatformDepRoutineByName(self, routineName):
        genericName = self._platformDepRoutineMappings.get(routineName)
        if genericName:
            return self._platformDepRoutines[genericName]
        return None

    def getPlatformDependentRoutineByName(self, routineName):
        genericRoutine = self.getGenericPlatformDepRoutineByName(routineName)
        if genericRoutine:
            return genericRoutine.getPlatformDepRoutineInfoByName(routineName)[0]
        return None

    # should be using trie structure for quick find, but
    # as python does not have trie and seems to be OK now
    def categorizeRoutineByNamespace(self, routineName):
        return self.__categorizeVariableNameByNamespace__(routineName)

    def categorizeGlobalByNamespace(self, globalName):
        return self.__categorizeVariableNameByNamespace__(globalName, True)

    def __categorizeVariableNameByNamespace__(self, variableName,
                                              isGlobal=False):
        for package in self._allPackages.itervalues():
            hasMatch = False
            matchNamespace = ""
            if isGlobal:
                for globalNameSpace in package.getGlobalNamespace():
                    if variableName.startswith(globalNameSpace):
                        return (globalNameSpace, package)
            for namespace in package.getNamespaces():
                if variableName.startswith(namespace):
                    hasMatch = True
                    matchNamespace = namespace
                if namespace.startswith("!"):
                    if not hasMatch:
                        break
                    elif variableName.startswith(namespace[1:]):
                        hasMatch = False
                        matchNamespace = ""
                        break
            if hasMatch:
                return (matchNamespace, package)
        return (None, None)

    def __generatePlatformDependentRoutineDependencies__(self):
        for genericRoutine in self._platformDepRoutines.itervalues():
            genericRoutine.setHasSourceCode(False)
            callerRoutines = genericRoutine.getCallerRoutines()
            for routineDict in callerRoutines.itervalues():
                for routine in routineDict.keys():
                    routineName = routine.getName()
                    if self.isPlatformDependentRoutineByName(routineName):
                        value = routineDict.pop(routine)
                        newRoutine = self.getGenericPlatformDepRoutineByName(routineName)
                        routineDict[newRoutine] = value

    def __fixPlatformDependentRoutines__(self):
        for routineName in self._platformDepRoutineMappings:
            if routineName in self._allRoutines:
                logger.info("Removing Routine: %s" % routineName)
                self._allRoutines.pop(routineName)

    def generateAllPackageDependencies(self):
        self.__fixPlatformDependentRoutines__()
        self.__generatePlatformDependentRoutineDependencies__()
        for package in self._allPackages.itervalues():
            package.generatePackageDependencies()
