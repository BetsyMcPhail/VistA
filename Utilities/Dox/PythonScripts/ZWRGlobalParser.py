#---------------------------------------------------------------------------
# Copyright 2012 The Open Source Electronic Health Record Agent
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
#---------------------------------------------------------------------------
import os
import sys
import re
from datetime import datetime

from LogManager import logger

class ItemValue(object):
  def __init__(self, value):
    self.value = value
    if value:
      self.value = value.split('^')
  def __len__(self):
    if self.value:
      return len(self.value)
    return 0
  def __contains__(self, elt):
    if self.value:
      return elt in self.value
    return False
  def __getitem__(self, key):
    if self.value:
      return self.value[key]
    return None
  def __str__(self):
    if self.value:
      return "^".join(self.value)
    elif self.value is None:
      return str(None)
    else:
      return ""

class GlobalNode(object):
  def __init__(self, value=None, subscript=None, parent=None):
    self.child = {}
    self.value = value
    self.subscript = subscript
    self.parent=parent
  def isRoot(self):
    return self.parent is None
  def getRootSubscript(self):
    if self.isRoot():
      return self.subscript
    else:
      return self.parent.getRootSubscript()
  def getRootNode(self):
    if self.isRoot():
      return self
    else:
      return self.parent.getRootNode()
  def get(self, key, default=None):
    return self.child.get(key, default)
  def __contains__(self, elt):
    return elt in self.child
  def __getitem__(self, key):
    return self.child[key]
  def __setitem__(self, key, value):
    self.child[key] = value
    value.subscript = key
    value.parent = self
  def __iter__(self):
    return iter(self.child)
  def __len__(self):
    return len(self.child)
  def keys(self):
    return self.child.keys()
  def values(self):
    return self.child.value()
  def getIndex(self):
    if self.parent:
      if self.parent.isRoot():
        outId = "%s%s" % (self.parent.getIndex(), self.subscript)
      else:
        outId = "%s,%s" % (self.parent.getIndex(), self.subscript)
    else:
      outId = "%s(" % self.subscript
    return outId
  def __str__(self):
    return "%s)=%s" % (self.getIndex(), self.value)
  def __sizeof__(self):
    return (sys.getsizeof(self.child) +
            sys.getsizeof(self.value) +
            sys.getsizeof(self.subscript))

def printGlobal(gNode):
  if gNode is not None:
    if gNode.value is not None: # skip intermediate node
      logger.info(gNode)
    for item in sorted(gNode, cmp=sortDataEntryFloatFirst):
      printGlobal(gNode[item])
  else:
    return

def countGlobal(gNode):
  sum = 1
  for item in gNode:
    sum += countGlobal(gNode[item])
  return sum

def countGlobalSize(gNode):
  size = sys.getsizeof(gNode)
  for item in gNode:
    size += countGlobalSize(gNode[item])
  return size

def sortDataEntryFloatFirst(data1, data2):
  isData1Float = convertToType(data1, float)
  isData2Float = convertToType(data2, float)
  if isData1Float and isData2Float:
    return cmp(float(data1), float(data2))
  if isData1Float:
    return -1 # float first
  if isData2Float:
    return 1
  return cmp(data1, data2)

def convertToType(data1, convertFunc):
  try:
    convertFunc(data1)
    return True
  except ValueError:
    return False

def getKeys(globalRoot, func=int):
  outKey = []
  for key in globalRoot:
    try:
      idx = func(key)
      outKey.append(key)
    except ValueError:
      pass
  return sorted(outKey, key=lambda x: func(x))

def createGlobalNodeByZWRFile(inputFileName):
  globalRoot = None
  with open(inputFileName, "r") as input:
    for idx, line in enumerate(input,0):
      if idx <=1:
        continue
      line = line.strip('\r\n')
      if idx == 2: globalRoot = GlobalNode(subscript=line[:line.find('(')])
      createGlobalNode(line, globalRoot)
  return globalRoot

def getCommonSubscript(one, two):
  if not one or not two:
    return []
  lessOne, moreOne = one, two
  if len(one) > len(two):
    lessOne, moreOne = two, one
  for idx, sub in enumerate(lessOne, 1):
    if moreOne[idx-1] != sub:
      idx = idx - 1
      break
  return lessOne[0:idx]

def resetGlobalIndex(subscripts, glbRootSub):
  index = 1
  if len(subscripts) == 1:
    logger.info("reset index to 0")
    index = 0
  elif glbRootSub == '^DD' and subscripts[0] == '0':
    logger.info("reset index to 0")
    index = 0
  return index

class DefaultZWRRootGenerator(object):
  def __init__(self, inputFileName, glbLoc=None):
    self.glbLoc = glbLoc
    self.curCommonSub = None
    if not glbLoc:
      self.index = 1 # set the starting index to be 1
      self.rootSub = None
      self.commonSubscript = None
    else:
      self.commonSubscript, value, self.rootSub = findSubscriptValue(glbLoc)
      if self.commonSubscript:
        self.index = len(self.commonSubscript)
      else:
        self.index = 0
    self.curRoot = None
    self.inputFile = open(inputFileName, "r")
    self.lineNo = 0

  def __iter__(self):
    return self
  def __del__(self):
    self.inputFile.close()
  def __next__(self):
    return self.next()

  def next(self):
    if self.inputFile.closed:
      raise StopIteration
    while True:
      line = self.inputFile.readline()
      if not line or len(line) == 0:
        self.inputFile.close()
        if self.curRoot:
          retNode = self.curRoot.getRootNode()
          if self.curCommonSub:
            common = self.curCommonSub[0:self.index]
            for sub in common:
              retNode = retNode[sub]
          elif self.commonSubscript:
            for sub in self.commonSubscript:
              retNode = retNode[sub]
          return retNode
      self.lineNo += 1
      if self.lineNo <= 2: # ignore the first two lines
        continue
      line = line.strip('\r\n')
      result = self.filterResult(line)
      if result is None:
        self.inputFile.close()
        raise StopIteration
      if result == True:
        continue
      if result:
        return result

  def filterResult(self, line):
    """
      return None to stop reading more information
      return False to keep reading more information
      return GlobalNode to generate the result
    """
    retNode = None
    subscripts, value, rootSub = findSubscriptValue(line)
    if not subscripts: # must have some subscripts
      logger.info("no subscription found %s" % line)
      return None
    if not self.rootSub:
      self.rootSub = rootSub
    if rootSub != self.rootSub: # not under the same root, ignore
      retNode = self.curRoot
      if self.glbLoc:
        logger.warn("Different root, expected: %s, real: %s, ignore for now" %
                      (self.rootSub, rootSub))
        self.curRoot = None
        return True
      else:
        self.rootSub = rootSub
        self.curCommonSub = subscripts[0:self.index+1]
        self.curRoot = createGlobalNode(line)
        if retNode:
          retNode = retNode.getRootNode()
          for sub in self.curCommonSub:
            retNode = retNode[sub]
          return retNode
        else:
          return True
    if self.commonSubscript and subscripts[0:self.index] != self.commonSubscript:
      logger.warn("Different subsript, expected: %s, real: %s, ignore for now" %
          (self.commonSubscript, subscripts[0:self.index]))
      retNode = self.curRoot
      self.curRoot = None
      if retNode:
        retNode = retNode.getRootNode()
        for sub in self.commonSubscript:
          retNode = retNode[sub]
        return retNode
      else:
        return True
    curCommonScript = getCommonSubscript(subscripts, self.curCommonSub)
    #logger.debug(curCommonScript, self.curCommonSub)
    if self.curCommonSub is None or self.curCommonSub == curCommonScript:
      if self.curCommonSub is None:
        self.curCommonSub = subscripts[0:self.index+1]
      self.curRoot = createGlobalNode(line, self.curRoot)
      return True
    else:
      retNode = self.curRoot
      if retNode:
        retNode = retNode.getRootNode()
        for subscript in curCommonScript:
          retNode = retNode[subscript]
      self.curRoot = createGlobalNode(line)
      self.curCommonSub = curCommonScript + subscripts[len(curCommonScript):self.index+1]
      return retNode

def readGlobalNodeFromZWRFileV2(inputFileName, glbLoc=None):
  return DefaultZWRRootGenerator(inputFileName, glbLoc)

def readGlobalNodeFromZWRFile(inputFileName):
  """ this is indeed a GlobalNode generator implemented by yield
      Assume all nodes subscript layout is always depth first
  """
  glbRootSub = None
  index = 1
  with open(inputFileName, "r") as input:
    curRoot, commonSubscript = None, None
    for idx, line in enumerate(input,0):
      if idx <=1:
        continue
      line = line.strip('\r\n')
      subscripts, value, rootSub = findSubscriptValue(line) # find all the subscripts
      if not subscripts:
        yield None
        return
      if idx == 2:
        glbRootSub = rootSub
        index = resetGlobalIndex(subscripts, glbRootSub)
      curCommonScript = getCommonSubscript(subscripts, commonSubscript)
      if not curCommonScript:
        commonSubscript = subscripts[0:index+1]
        logger.debug("com sub: %s, index is %s" % (commonSubscript, index))
      if curCommonScript != commonSubscript:
        retNode = curRoot
        if curCommonScript:
          commonSubscript = curCommonScript + subscripts[len(curCommonScript):index+1]
        curRoot = createGlobalNode(line)
        if retNode:
          yield retNode
      else:
        if not curRoot:
          curRoot = GlobalNode(subscript=glbRootSub)
        createGlobalNode(line, curRoot)
    """
      yield the last part of the global if any
    """
    if curRoot:
      yield curRoot

def findSubscriptValue(inputLine):
  """
    Seperate the subscript part vs value part of the global line
    ^DD(0,"IX",5)="1^^3^7" should return
    [0, IX, 5], 1^^3^7, ^DD
  """
  start = inputLine.find("(")
  if start <= 0:
    return None, None, inputLine
  if start == len(inputLine) - 1:
    return None, None, inputLine[:-1]
  pos = inputLine.find(")=\"")
  if pos > start+1:
    nodeIndex = [x.strip('"') for x in inputLine[start+1:pos].split(",")]
    nodeValue = inputLine[pos+3:-1]
    return nodeIndex, nodeValue, inputLine[:start]
  else:
    nodeIndex = [x.strip('"') for x in inputLine[start+1:].split(",")]
    return nodeIndex, None, inputLine[:start]

def createGlobalNode(inputLine, globalRoot=None):
  """
    create Global Node based on the input
    if globalRoot is None, it should result the root
    node created.
  """
  retRoot = globalRoot
  nodeIndex, nodeValue, nodeRoot = findSubscriptValue(inputLine)
  if nodeIndex:
    if nodeValue and len(nodeValue) > 0:
      nodeValue = nodeValue.replace('""', '"')
    if not globalRoot:
      logger.debug("Creating a new globalRoot %s" % inputLine)
      retRoot = GlobalNode(subscript=nodeRoot)
      nodeIdx = retRoot
    else:
      logger.debug("finding a new globalRoot")
      nodeIdx = retRoot.getRootNode()
      logger.debug("The root is %s" % nodeIdx.subscript)
      if nodeIdx.subscript != nodeRoot:
        logger.error("Global Node root subscript mismatch: %s, %s" %
                      (nodeRoot, nodeIdx.subscript))
    for idx in nodeIndex[:-1]:
      if idx not in nodeIdx:
        nodeIdx[idx] = GlobalNode()
      nodeIdx = nodeIdx[idx]
    nodeIdx[nodeIndex[-1]] = GlobalNode(nodeValue)
  return retRoot