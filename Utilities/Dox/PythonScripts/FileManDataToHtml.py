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
import os
import sys
import re
from datetime import datetime
import logging
import glob
import cgi

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.normpath(os.path.join(FILE_DIR, "../../../Scripts"))
print SCRIPTS_DIR
if SCRIPTS_DIR not in sys.path:
  sys.path.append(SCRIPTS_DIR)

from FileManDateTimeUtil import fmDtToPyDt
from ZWRGlobalParser import getKeys
from CrossReference import FileManField
from WebPageGenerator import getRoutineHtmlFileName, normalizePackageName

def safeFileName(name):
  """ convert to base64 encoding """
  import base64
  return base64.urlsafe_b64encode(name)

def safeElementId(name):
  import base64
  """
  it turns out that '=' is not a valid html element id
  remove the padding
  """
  return base64.b64encode(name, ["_", "_"]).replace('=','')
"""
  html header using JQuery Table Sorter Plugin
  http://tablesorter.com/docs/
"""

table_sorter_header="""
<link rel="stylesheet" href="http://tablesorter.com/themes/blue/style.css" type="text/css" id=""/>
<script type="text/javascript" src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
<script type="text/javascript" src="http://tablesorter.com/__jquery.tablesorter.js"></script>
<script type="text/javascript" id="js">
  $(document).ready(function() {
  // call the tablesorter plugin
  $("#rpctable").tablesorter({
    // sort on the first column and third column, order asc
    sortList: [[0,0],[2,0]]
  });
}); </script>
"""

"""
  html header using JQuery DataTable Plugin
  https://datatables.net/
"""
data_table_reference = """
<link rel="stylesheet" href="../datatable/css/demo_page.css" type="text/css" id=""/>
<link rel="stylesheet" href="../datatable/css/demo_table.css" type="text/css" id=""/>
<link rel="stylesheet" href="../style.css" type="text/css" id=""/>
<script type="text/javascript" src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
<script type="text/javascript" src="../datatable/js/jquery.dataTables.js"></script>
"""

from string import Template

data_table_list_init_setup = Template("""
<script type="text/javascript" id="js">
  $$(document).ready(function() {
  // call the tablesorter plugin
      $$("#${tableName}").dataTable({
        "bInfo": true,
        "iDisplayLength": 25,
        "sPaginationType": "full_numbers",
        "bStateSave": true,
        "bAutoWidth": true
      });
}); </script>
""")

data_table_large_list_init_setup = Template("""
<script type="text/javascript" id="js">
  $$(document).ready(function() {
  // call the tablesorter plugin
      $$("#${tableName}").dataTable({
        "bProcessing": true,
        "bStateSave": true,
        "iDisplayLength": 10,
        "sPaginationType": "full_numbers",
        "bDeferRender": true,
        "sAjaxSource": "${ajexSrc}"
      });
}); </script>
""")

data_table_record_init_setup = Template("""
<script type="text/javascript" id="js">
  $$(document).ready(function() {
  // call the tablesorter plugin
      $$("#${tableName}").dataTable({
        "bPaginate": false,
        "bLengthChange": false,
        "bInfo": false,
        "bStateSave": true,
        "bSort": false
      });
}); </script>
""")

def test_sub():
  print data_table_large_list_init_setup.substitute(ajexSrc="Test", tableName="Test")
  print data_table_list_init_setup.substitute(tableName="Test")
  print data_table_record_init_setup.substitute(tableName="Test")


def outputDataListTableHeader(output, tName):
  output.write("%s\n" % data_table_reference)
  initSet = data_table_list_init_setup.substitute(tableName=tName)
  output.write("%s\n" % initSet)

def outputLargeDataListTableHeader(output, src, tName):
  output.write("%s\n" % data_table_reference)
  initSet = data_table_large_list_init_setup.substitute(ajexSrc=src,
                                                        tableName=tName)
  output.write("%s\n" % initSet)

def outputDataRecordTableHeader(output, tName):
  output.write("%s\n" % data_table_reference)
  initSet = data_table_record_init_setup.substitute(tableName=tName)
  output.write("%s\n" % initSet)

def outputFileEntryTableList(output, tName):
  output.write("<div id=\"demo\">")
  output.write("<table id=\"%s\" class=\"display\">\n" % tName)
  output.write("<thead>\n")
  output.write("<tr>\n")
  for name in ("Name", "Value"):
    output.write("<th>%s</th>\n" % name)
  output.write("</tr>\n")
  output.write("</thead>\n")

dox_url = "http://code.osehra.org/dox/"

def getDataEntryHtmlFile(dataEntry, ien, fileNo):
  entryName = str(dataEntry.name)
  return getDataEntryHtmlFileByName(entryName, ien, fileNo)

def getDataEntryHtmlFileByName(entryName, ien, fileNo):
  entryName = entryName[:20] # max 20 chars
  return ("%s-%s" % (fileNo, ien)) + ".html"

def getFileHtmlLink(dataEntry, value):
  entryName = str(value)
  htmlFile = getDataEntryHtmlFileByName(entryName, dataEntry.ien,
                                        dataEntry.fileNo)
  return "<a href=\"%s\">%s</a>" % (htmlFile, value)

def getRoutineHRefLink(dataEntry, routineName):
  return "<a href=\"%s%s\">%s</a>" % (dox_url,
                                      getRoutineHtmlFileName(routineName),
                                      routineName)

def getWordProcessingDataBrief(dataEntry, value):
  return getWordProcessingData(value, False)
def getWordProcessingData(value, isList=True):
  outValue = " ".join(value)
  if isList:
    outValue = "<pre>\n" + cgi.escape(outValue) + "\n</pre>\n"
  return outValue

def getFileManFilePointerLink(dataEntry, value):
  if value:
    fields = value.split('^')
    if len(fields) == 3: # fileNo, ien, name
      refFile = getDataEntryHtmlFileByName(fields[2], fields[1], fields[0])
      value = '<a href="%s">%s</a>' % (refFile, fields[-1])
    elif len(fields) == 2:
      value = 'File: %s, IEN: %s' % (fields[0], fields[1])
    else:
      logging.error("Unknown File Pointer Value %s" % value)
  return value
"""
fields and logic to convert to html for RPC List
"""
rpc_list_fields = (("Name", '.01', getFileHtmlLink), # Name
       ("Tag", '.02', None), # Tag
       ("Routine", '.03', getRoutineHRefLink), # Routine
       ("Availability", '.05', None),# Availability
       #("Description", '1', getWordProcessingDataBrief),# Description
   )

"""
fields and logic to convert to html for HL7 List
"""
hl7_list_fields = (
       ("Name", '.01', getFileHtmlLink), # Name
       ("Type", '4', None), # Type
       ("Event Type", '770.4', getFileManFilePointerLink), # Event Type
       ("Transaction Message Type", '770.3', getFileManFilePointerLink), # Message Type
       #("Response Message Type", '770.11', getFileManFilePointerLink), # Message Type
       ("Sender", '770.1', getFileManFilePointerLink),# Sending Application
       ("Receiver", '770.2', getFileManFilePointerLink),# Receiving Application
   )

def outputDataTableHeader(output, name_list, tName):
  output.write("<div id=\"demo\">")
  output.write("<table id=\"%s\" class=\"display\">\n" % tName)
  output.write("<thead>\n")
  output.write("<tr>\n")
  for name in name_list:
    output.write("<th>%s</th>\n" % name)
  output.write("</tr>\n")
  output.write("</thead>\n")

def writeTableListInfo(output, tName):
  output.write("<div id=\"demo\">")
  output.write("<table id=\"%s\" class=\"display\">\n" % tName)
  output.write("<thead>\n")
  output.write("<tr>\n")
  for name in ("Name", "IEN"):
    output.write("<th>%s</th>\n" % name)
  output.write("</tr>\n")
  output.write("</thead>\n")

def generateRPCListHtml(dataEntryLst, pkgName, outDir):
  """
    Specific logic to handle RPC List
    @TODO move the logic to a specific file
  """

  return generateDataListByPackage(dataEntryLst,
                                   pkgName, outDir,
                                   rpc_list_fields, "RPC")

def generateHL7ListByPackage(dataEntryLst, pkgName, outDir):
  """
    Specific logic to handle HL7 List
    @TODO move the logic to a specific file
  """
  return generateDataListByPackage(dataEntryLst,
                                   pkgName, outDir,
                                   hl7_list_fields, "HL7")

def generateDataListByPackage(dataEntryLst, packageName, outDir, list_fields, listName):
  with open("%s/%s-%s.html" % (outDir, packageName, listName), 'w+') as output:
      output.write("<html>\n")
      tName = safeElementId("%s-%s" % (listName, packageName))
      outputDataListTableHeader(output, tName)
      output.write("<body id=\"dt_example\">")
      output.write("""<div id="container" style="width:80%">""")
      output.write("<h1>Package: %s %s List</h1>" % (getPackageHRefLink(packageName), listName))
      outputDataTableHeader(output, [x[0] for x in list_fields], tName)
      """ table body """
      output.write("<tbody>\n")
      for dataEntry in dataEntryLst:
        tableRow = [""]*len(list_fields)
        allFields = dataEntry.fields
        output.write("<tr>\n")
        for idx, id in enumerate(list_fields):
          if id[1] in allFields:
            value = allFields[id[1]].value
            if id[-1]:
              value = id[-1](dataEntry, value)
            tableRow[idx] = value
        for item in tableRow:
          #output.write("<td class=\"ellipsis\">%s</td>\n" % item)
          output.write("<td>%s</td>\n" % item)
        output.write("</tr>\n")
      output.write("</tbody>\n")
      output.write("</table>\n")
      output.write("</div>\n")
      output.write("</div>\n")
      output.write ("</body></html>\n")

def getPackageHRefLink(pkgName):
  from WebPageGenerator import getPackageHtmlFileName
  value = "<a href=\"%s%s\">%s</a>" % (dox_url,
                                       getPackageHtmlFileName(pkgName),
                                       pkgName)
  return value

def generateDataTableHtml(fileManData, fileNo, outDir):
  isLargeFile = len(fileManData.dataEntries) > 4500
  tName = normalizePackageName(fileManData.name)
  with open("%s/%s.html" % (outDir, fileNo), 'w') as output:
    output.write("<html>\n")
    if isLargeFile:
      ajexSrc = "%s_array.txt" % fileNo
      outputLargeDataListTableHeader(output, ajexSrc, tName)
    else:
      outputDataListTableHeader(output, tName)
    output.write("<body id=\"dt_example\">")
    output.write("""<div id="container" style="width:80%">""")
    output.write("<h1>File %s(%s) Data List</h1>" % (tName, fileNo))
    writeTableListInfo(output, tName)
    if not isLargeFile:
      output.write("<tbody>\n")
      for ien in getKeys(fileManData.dataEntries.keys(), float):
        dataEntry = fileManData.dataEntries[ien]
        if not dataEntry.name:
          logging.warn("no name for %s" % dataEntry)
          continue
        name = dataEntry.name
        if isFilePointerType(dataEntry):
          link, name = convertFilePointerToHtml(dataEntry.name)
        dataHtmlLink = "<a href=\"%s\">%s</a>" % (getDataEntryHtmlFile(dataEntry, ien, fileNo),
                                                  name)
        tableRow = [dataHtmlLink, dataEntry.ien]
        output.write("<tr>\n")
        """ table body """
        for item in tableRow:
          output.write("<td>%s</td>\n" % item)
        output.write("</tr>\n")
    output.write("</tbody>\n")
    output.write("</table>\n")
    output.write("</div>\n")
    output.write("</div>\n")
    output.write ("</body></html>\n")
  if isLargeFile:
    import json
    logging.info("Ajex source file: %s" % ajexSrc)
    """ Write out the data file in JSON format """
    outJson = {"aaData": []}
    with open(os.path.join(outDir, ajexSrc), 'w') as output:
      outArray =  outJson["aaData"]
      for ien in getKeys(fileManData.dataEntries.keys(), float):
        dataEntry = fileManData.dataEntries[ien]
        if not dataEntry.name:
          logging.warn("no name for %s" % dataEntry)
          continue
        name = dataEntry.name
        if isFilePointerType(dataEntry):
          link, name = convertFilePointerToHtml(dataEntry.name)
        dataHtmlLink = "<a href=\"%s\">%s</a>" % (getDataEntryHtmlFile(dataEntry, ien, fileNo),
                                                  name)
        outArray.append([dataHtmlLink, ien])
      json.dump(outJson, output)
def isFilePointerType(dataEntry):
  if dataEntry and dataEntry.type:
    return ( dataEntry.type == FileManField.FIELD_TYPE_FILE_POINTER or
             dataEntry.type == FileManField.FIELD_TYPE_VARIABLE_FILE_POINTER )
  return False
def convertFileManDataToHtml(fileManData, outDir):
  for ien in getKeys(fileManData.dataEntries.keys(), float):
    tName = safeElementId("%s-%s" % (fileManData.fileNo, ien))
    dataEntry = fileManData.dataEntries[ien]
    if not dataEntry.name:
      logging.warn("no name for %s" % dataEntry)
      continue
    name = dataEntry.name
    if isFilePointerType(dataEntry):
      link, name = convertFilePointerToHtml(dataEntry.name)
    outHtmlFileName = getDataEntryHtmlFile(dataEntry, ien, fileManData.fileNo)
    with open("%s/%s" % (outDir, outHtmlFileName), 'w') as output:
      output.write ("<html>")
      outputDataRecordTableHeader(output, tName)
      output.write("<body id=\"dt_example\">")
      output.write("""<div id="container" style="width:80%">""")
      output.write ("<h1>%s (%s) &nbsp;&nbsp;  %s (%s)</h1>\n" % (name, ien,
                                                        fileManData.name,
                                                        fileManData.fileNo))
      outputFileEntryTableList(output, tName)
      """ table body """
      output.write("<tbody>\n")
      fileManDataEntryToHtml(output, dataEntry, True)
      output.write("</tbody>\n")
      output.write("</table>\n")
      output.write("</div>\n")
      output.write("</div>\n")
      output.write ("</body></html>")

def convertFileManSubFileDataToHtml(output, fileManData):
  output.write ("<ol>\n")
  for ien in getKeys(fileManData.dataEntries.keys(), float):
    dataEntry = fileManData.dataEntries[ien]
    fileManDataEntryToHtml(output, dataEntry, False)
  output.write ("</ol>\n")

regexRtn = re.compile("( ?D |[ :']\$\$)(?P<tag>([A-Z0-9][A-Z0-9]*)?)\^(?P<rtn>[A-Z%][A-Z0-9]+)")
def getMumpsRoutineHtmlLink(inputString):
  import re
  output = ""
  pos = 0
  endpos = 0
  for result in regexRtn.finditer(inputString):
    if result:
      routine = result.group('rtn')
      if routine:
        tag = result.group('tag')
        start, end = result.span('rtn')
        endpos = result.end()
        output += inputString[pos:start] + getRoutineHRefLink(None, routine) + inputString[end:endpos]
        pos = endpos
  if endpos != 0 and endpos < len(inputString):
    output += inputString[endpos:]
  if output:
    return output
  else:
    return inputString

def fileManDataEntryToHtml(output, dataEntry, isRoot):
  if not isRoot:
    output.write ("<li>\n")
  for fldId in sorted(dataEntry.fields.keys(), key=lambda x: float(x)):
    dataField = dataEntry.fields[fldId]
    fieldType = dataField.type
    name, value = dataField.name, dataField.value
    """ hack for RPC """
    if isRoot and fldId == '.03' and dataField.name == "ROUTINE":
      value = getRoutineHRefLink(dataEntry, value)
    elif fieldType == FileManField.FIELD_TYPE_MUMPS:
      value = getMumpsRoutineHtmlLink(value)
    elif fieldType == FileManField.FIELD_TYPE_SUBFILE_POINTER:
      if value and value.dataEntries:
        if isRoot:
          output.write ("<tr>\n")
          output.write("<td>%s</td>\n" % name)
          output.write("<td>\n")
        else:
          output.write ("<dl><dt>%s:</dt>\n" % name)
          output.write ("<dd>\n")
        convertFileManSubFileDataToHtml(output, value)
        if isRoot:
          output.write("</td>\n")
          output.write ("</tr>\n")
        else:
          output.write ("</dd></dl>\n")
      continue
    elif (fieldType == FileManField.FIELD_TYPE_FILE_POINTER or
          fieldType == FileManField.FIELD_TYPE_VARIABLE_FILE_POINTER) :
      if value:
        origVal = value
        value, tmp = convertFilePointerToHtml(value)
    elif fieldType == FileManField.FIELD_TYPE_WORD_PROCESSING:
      value = "\n".join(value)
      value = "<pre>\n" + cgi.escape(value) + "\n</pre>\n"
    if isRoot:
      output.write ("<tr>\n")
      output.write ("<td>%s</td>\n" % name)
      output.write ("<td>%s</td>\n" % value)
      output.write ("</tr>\n")
    else:
      output.write ("<dt>%s:  &nbsp;&nbsp;%s</dt>\n" % (name, value))
      #output.write ("<dd>%s</dd>\n" % value)
  if not isRoot:
    output.write("</li>\n")

def convertFilePointerToHtml(inputValue):
  value = inputValue
  name = inputValue
  fields = inputValue.split('^')
  if len(fields) == 3: # fileNo, ien, name
    refFile = getDataEntryHtmlFileByName(fields[2], fields[1], fields[0])
    value = '<a href="%s">%s</a>' % (refFile, fields[-1])
    name = fields[-1]
  elif len(fields) == 2:
    value = 'File: %s, IEN: %s' % (fields[0], fields[1])
    name = value
  else:
    logging.error("Unknown File Pointer Value %s" % inputValue)
  return value, name
def test_convertFilePointerToHtml():
  input = ('1^345^Testing', '2^345', '5')
  for one in input:
    print convertFilePointerToHtml(one)
def outputFileManDataAsHtml(fileManDataMap, outDir, crossRef):
  """
    This is the entry pointer to generate Html output
    format based on FileMan Data object
    @TODO: integrate with FileManFileOutputFormat.py
  """
  for fileNo in getKeys(fileManDataMap.iterkeys(), float):
    fileManData = fileManDataMap[fileNo]
    if fileNo == '8994':
      if crossRef:
        allPackages = crossRef.getAllPackages()
        for package in allPackages.itervalues():
          if package.rpcs:
            logging.info("generating RPC list for package: %s"
                         % package.getName())
            generateRPCListHtml(package.rpcs, package.getName(), outDir)
    elif fileNo == '101':
      if crossRef:
        allPackages = crossRef.getAllPackages()
        for package in allPackages.itervalues():
          if package.hl7:
            logging.info("generating HL7 list for package: %s"
                         % package.getName())
            generateHL7ListByPackage(package.hl7, package.getName(), outDir)
    generateDataTableHtml(fileManData, fileNo, outDir)
    convertFileManDataToHtml(fileManData, outDir)

def test_safeElementId():
  for input in ("01", "1.0", "99999.4"):
    print safeElementId(input)

def test_getMumpsRoutineHtmlLink():
  for input in ('D ^TEST1',
                'D ^%ZOSV',
                'D TAG^TEST2',
                'Q $$TST^%RRST1',
                'D ACKMSG^DGHTHLAA',
                'S XQORM(0)="1A",XQORM("??")="D HSTS^ORPRS01(X)"',
                'I $$TEST^ABCD D ^EST Q:$$ENG^%INDX K ^DD(0)',
                'S DUZ=1 K ^XUTL(0)',
                """W:'$$TM^%ZTLOAD() *7,!!,"WARNING -- TASK MANAGER DOESN'T SEEM TO BE RUNNING!!!!",!!,*7""",
                ):
     print getMumpsRoutineHtmlLink(input)

def main():
  test_sub()
  test_safeElementId()
  test_convertFilePointerToHtml()
  test_getMumpsRoutineHtmlLink()

if __name__ == '__main__':
  main()
