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
import logging

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
    #self.value = ItemValue(value)
    self.value = value
    self.subscript = subscript
    self.parent=parent
  def isRoot(self):
    return self.parent is None
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
      logging.info(gNode)
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

def testGlobalNode():
  gn = GlobalNode("root^test", "^ZZTEST")
  for i in range(len(gn.value)):
    print gn.value[i]
  gn['test'] = GlobalNode("-1")
  for i in xrange(0,5):
    gn['test'][i] = GlobalNode(str(i)+'^')
    for j in xrange(0,5):
      gn['test'][i][j] = GlobalNode("^".join([str(i), str(j)]))
    print len(gn['test'][i].value)
  print len(gn)
  print len(gn['test'])
  print gn['test'].get(6)
  print gn['test'][2]
  print gn['test'][3]
  print 2 in gn['test']
  print(gn)
  printGlobal(gn)
  print "Total Global is %s" % countGlobal(gn)

def test_sortDataEntryFloatFirst():
  initLst = ['PRE', 'DIST', '22', '1', '0', 'INIT', 'VERSION', '4', 'INI', '%D', '%']
  sortedLst = sorted(initLst, cmp=sortDataEntryFloatFirst)
  print initLst, sortedLst

def getKeys(globalRoot, func=int):
  outKey = []
  for key in globalRoot:
    try:
      idx = func(key)
      outKey.append(key)
    except:
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

def test_getCommonSubscript():
  testOne = [0,1,2,3]
  testTwo = [0,3]
  testThree = [-1,1]
  testFour = None
  print getCommonSubscript(testOne, testTwo)
  print getCommonSubscript(testOne, testThree)
  print getCommonSubscript(testOne, testFour)

def resetGlobalIndex(subscripts, glbRootSub):
  index = 1
  if len(subscripts) == 1:
    logging.info("reset index to 0")
    index = 0
  elif glbRootSub == '^DD' and subscripts[0] == '0':
    logging.info("reset index to 0")
    index = 0
  return index

def readGlobalNodeFromZWRFile(inputFileName):
  """ this is indeed a GlobalNode generator implemented by yield
      Assume all nodes are under the exact same root like ^DIC(
      and node subscript layout is always depth first
  """
  glbRootSub = None
  index = 1
  with open(inputFileName, "r") as input:
    curRoot, commonSubscript = None, None
    for idx, line in enumerate(input,0):
      if idx <=1:
        continue
      line = line.strip('\r\n')
      subscripts = findSubscriptValue(line)[0] # find all the subscripts
      if not subscripts:
        yield None
        return
      if idx == 2:
        glbRootSub = line[:line.find('(')]
        index = resetGlobalIndex(subscripts, glbRootSub)
      if not subscripts:
        logging.warn("no subscripts for %s" % line)
        continue # ignore things that does not have subscript
      curCommonScript = getCommonSubscript(subscripts, commonSubscript)
      if not curCommonScript:
        commonSubscript = subscripts[0:index+1]
        logging.debug("com sub: %s, index is %s" % (commonSubscript, index))
      if curCommonScript != commonSubscript:
        retNode = curRoot
        if curCommonScript:
          commonSubscript = curCommonScript + subscripts[len(curCommonScript):index+1]
        curRoot = GlobalNode(subscript=glbRootSub)
        createGlobalNode(line, curRoot)
        if retNode:
          yield retNode
          del retNode
          retNode = None
      else:
        if not curRoot:
          curRoot = GlobalNode(subscript=glbRootSub)
        createGlobalNode(line, curRoot)
    """
      yield the last part of the global
    """
    if curRoot:
      yield curRoot

def test_createGlobalNodeByZWRFile(inputFileName):
  logging.info("start parsing file: %s" % inputFileName)
  outGlobal = createGlobalNodeByZWRFile(inputFileName)
  print "Total Global is %s" % countGlobal(outGlobal)
  print "Total size of Global is %s" % countGlobalSize(outGlobal)
  logging.info("end parsing file: %s" % inputFileName)

def test_readGlobalNodeFromZWRFile(inputFileName):
  logging.info("Start reading file: %s" % inputFileName)
  totalEntry = 0
  for globalRoot in readGlobalNodeFromZWRFile(inputFileName):
    if globalRoot:
      totalEntry += 1
      #printGlobal(globalRoot)
      del globalRoot
      globalRoot = None
      pass
  logging.info("Total # of entries: %s" % totalEntry)
  logging.info("End reading file: %s" % inputFileName)

def findSubscriptValue(inputLine):
  """
    Seperate the subscript part vs value part of the global line
    ^DD(0,"IX",5)="1^^3^7" should return
    [0, IX, 5] and 1^^3^7
  """
  start = inputLine.find("(")
  if start <= 0:
    return None, None
  pos = inputLine.find(")=\"")
  if pos >= start:
    nodeIndex = [x.strip('"') for x in inputLine[start+1:pos].split(",")]
    nodeValue = inputLine[pos+3:-1]
    return nodeIndex, nodeValue
  else:
    return None, None

def test_findSubscriptValue():
  for line in [
    '''^DD(0,0)="ATTRIBUTE^N^^35"''',
    '''^DD(0,0,"IX","SB",0,.2)=""''',
  ]:
    print findSubscriptValue(line)

def createGlobalNode(inputLine, globalRoot):
  """
  """
  nodeIndex, nodeValue = findSubscriptValue(inputLine)
  if nodeIndex:
    if len(nodeValue) > 0:
      nodeValue = nodeValue.replace('""', '"')
    nodeIdx = globalRoot
    for idx in nodeIndex[:-1]:
      if idx not in nodeIdx:
        nodeIdx[idx] = GlobalNode()
      nodeIdx = nodeIdx[idx]
    nodeIdx[nodeIndex[-1]] = GlobalNode(nodeValue)
  else:
    return

def test_createGlobalNode():
  for line in [
    '''^DD(0,0)="ATTRIBUTE^N^^35"''',
    '''^DD(0,0,"IX","SB",0,.2)=""''',
  ]:
    curNode = GlobalNode(subscript="^DD")
    createGlobalNode(line, curNode)
    printGlobal(curNode)

def test_UtilitiesFunctions():
  testGlobalNode()
  test_findSubscriptValue()
  test_createGlobalNode()

def main():
  from LogManager import initConsoleLogging
  import sys
  from datetime import datetime
  initConsoleLogging(formatStr='%(asctime)s %(message)s')
  #test_UtilitiesFunctions()
  #test_createGlobalNodeByZWRFile(sys.argv[1])
  test_readGlobalNodeFromZWRFile(sys.argv[1])

if __name__ == '__main__':
  main()
