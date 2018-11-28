#---------------------------------------------------------------------------
# Copyright 2014 The Open Source Electronic Health Record Agent
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

from datetime import datetime
import json
import re
import xlrd
from xlrd import xldate_as_tuple

ROOT_NODE = {}
ROOT_NODE["None"] = []

def convertToInt(value,index):
  try:
    return int(value)
  except ValueError:
    return value

def convertToDate(value):
  dateValue = xldate_as_tuple(value, 0)
  return datetime(*dateValue).strftime("%Y-%m-%d")

def convertToBool(value):
  if value:
    return "TRUE"
  return "FALSE"

# Removes any bracketed numbers from the name, if it exists
def checkEmpty(value, index):
  if index == 5:
    return ["None"]
  # TODO: Need to return something here

def parseStringVal(value, index):
  if index == 5:
    returnArray=[]
    for bffValue in re.split("(,[ ]+|^)[0-9]+: ",value):
      bffValue = bffValue.strip()
      if re.match(',[ ]*',bffValue) or (bffValue == ''):
        continue
      if not bffValue in returnArray:
        returnArray.append(bffValue)
      if not bffValue in ROOT_NODE:
        ROOT_NODE[bffValue] = []
    return returnArray
  elif index == 4:
    returnArray=[]
    for nsrEntry in value.split("\n"):
      if not nsrEntry in returnArray:
        returnArray.append(nsrEntry)
    return returnArray
  if not value.find(" [") == -1:
    return value[:value.find(" [")]
  return value

TYPE_DICT_CONVERT = {
  xlrd.XL_CELL_NUMBER: convertToInt,
  xlrd.XL_CELL_TEXT: parseStringVal,
  xlrd.XL_CELL_DATE: convertToDate,
  xlrd.XL_CELL_BLANK: checkEmpty,
  xlrd.XL_CELL_EMPTY: checkEmpty,
  xlrd.XL_CELL_ERROR: None,
  xlrd.XL_CELL_BOOLEAN: convertToBool,
}

# convert the excel name fields to standard json output name
REQUIREMENTS_FIELDS_CONVERT = {
  "RDM RDNG ID" : 'busNeedId',
  "ID" : 'busNeedId',
  "ARTIFACT TYPE" : 'type',
  "RDNG Artifact" : 'type',
  "NAME" : 'name',
  "PRIMARY TEXT": 'description',
  "NEW SERVICE REQUEST (NSR)": 'NSRLink',
  "BUSINESS FUNCTION (BFF)":"BFFlink",
  "Summary" : 'name',
  "Full Description": 'description',
  "NSR": 'NSRLink',
  "Associated BFF(s)":"BFFlink"
}

def checkReqForUpdate(curNode, pastJSONObj, curDate):
  diffFlag = False
  foundDate = curDate
  noHistory = False
  BFFList = []
  if type(curNode['BFFlink']) is list:
    for BFFlink in curNode['BFFlink']:
      BFFList.append(BFFlink)
  else:
    BFFList.append(curNode['BFFlink'])
  # Check past information for the object and compare the two
  # Remove all recentUpdate attributes
  for BFFEntry in BFFList:
    if pastJSONObj:
      diffFlag = False
      noHistory = False
      if BFFEntry in pastJSONObj:
        ret = filter(lambda x: x['name'] == curNode['name'] , pastJSONObj[BFFEntry])
        if ret:
          for entry in ret:
            diffFlag=False
            if "dateUpdated" in entry:
              foundDate=entry["dateUpdated"]
            for val in curNode.keys():
              if val in ["recentUpdate","dateUpdated"]:
                continue
              oldVal = entry[val] if (val in entry) else None
              newVal = curNode[val]
              if type(oldVal) == list:
                oldVal.sort()
                newVal.sort()
              if not oldVal == newVal:
                diffFlag= True
          else:
            # TODO: We'll never get here (no break in loop)
            noHistory = True
    if diffFlag:
      curNode['recentUpdate'] = "Update"
      curNode['dateUpdated']  = curDate
    else:
      curNode['recentUpdate'] = "None" if (noHistory) else "New Requirement"
      curNode['dateUpdated']= foundDate
    ROOT_NODE[BFFEntry].append(curNode)

def requirementsFieldsConvertFunc(x):
  if x in REQUIREMENTS_FIELDS_CONVERT:
    return REQUIREMENTS_FIELDS_CONVERT[x]
  return x

def convertExcelToJson(filename, output, pastData, curDate):
  pastJSONObj={}
  if pastData:
    with open(pastData,"r") as pastJSON:
      pastJSONObj = json.load(pastJSON)
  book = xlrd.open_workbook(filename)
  sheet = book.sheet_by_index(0)
  data_row = 1
  row_index= 0
  fields = None
  fields = sheet.row_values(row_index)
  fields = map(requirementsFieldsConvertFunc, fields)
  # Read rest of the BFF data from data_row
  for row_index in xrange(data_row, sheet.nrows):
    curNode = dict()
    curNode['isRequirement'] = True
    curNode['isRequirement'] = True
    for col_index in xrange(sheet.ncols):
      cell = sheet.cell(row_index, col_index)
      convFunc = TYPE_DICT_CONVERT.get(cell.ctype)
      cValue = cell.value
      if type(cValue) == unicode:
        cValue = re.sub(r'[^\x00-\x7F]+','', cValue) #cValue.decode('unicode_escape').encode('ascii','ignore')
      if convFunc:
        cValue = convFunc(cValue,col_index)
      if not cValue:
        continue
      curNode[fields[col_index]] = cValue
    checkReqForUpdate(curNode,pastJSONObj,curDate)

  with open(output, "w") as outputJson:
    json.dump(ROOT_NODE, outputJson)
