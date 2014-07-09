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

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.normpath(os.path.join(FILE_DIR, "../../../Scripts"))
print SCRIPTS_DIR
if SCRIPTS_DIR not in sys.path:
  sys.path.append(SCRIPTS_DIR)

from FileManDateTimeUtil import fmDtToPyDt
from ZWRGlobalParser import getKeys
from CrossReference import FileManField

def safeFileName(name):
  """ convert to base64 encoding """
  import base64
  return base64.urlsafe_b64encode(name)

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
dthead = """
<link rel="stylesheet" href="../datatable/css/demo_page.css" type="text/css" id=""/>
<link rel="stylesheet" href="../datatable/css/demo_table.css" type="text/css" id=""/>
<link rel="stylesheet" href="../style.css" type="text/css" id=""/>
<script type="text/javascript" src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
<script type="text/javascript" src="../datatable/js/jquery.dataTables.js"></script>
<script type="text/javascript" id="js">
  $(document).ready(function() {
  // call the tablesorter plugin
      $("#rpctable").dataTable({
        "bInfo": true,
        "iDisplayLength": 25,
        "sPaginationType": "full_numbers",
        "bStateSave": true,
        "bAutoWidth": false
      });

}); </script>
"""

dthead_rpc = """
<link rel="stylesheet" href="../datatable/css/demo_page.css" type="text/css" id=""/>
<link rel="stylesheet" href="../datatable/css/demo_table.css" type="text/css" id=""/>
<script type="text/javascript" src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
<script type="text/javascript" src="../datatable/js/jquery.dataTables.js"></script>
<script type="text/javascript" id="js">
  $(document).ready(function() {
  // call the tablesorter plugin
      $("#rpctable").dataTable({
        "bPaginate": false,
        "bLengthChange": false,
        "bInfo": false,
        "bStateSave": true,
        "bSort": false
      });

}); </script>
"""

def outputFileEntryTableList(output):
  #output.write("<table id=\"rpctable\" class=\"tablesorter\">\n")
  output.write("<div id=\"demo\">")
  output.write("<table id=\"rpctable\" class=\"display\">\n")
  output.write("<thead>\n")
  output.write("<tr>\n")
  for name in ("Name", "Value"):
    output.write("<th>%s</th>\n" % name)
  output.write("</tr>\n")
  output.write("</thead>\n")

dox_url = "http://code.osehra.org/dox/"
def getRPCHRefLink(value):
  return "<a href=\"%s.html\">%s</a>" % (safeFileName(value), value)

def getRoutineHRefLink(routineName):
  from WebPageGenerator import getRoutineHtmlFileName
  return "<a href=\"%s%s\">%s</a>" % (dox_url,
                                      getRoutineHtmlFileName(routineName),
                                      routineName)

def getWordProcessingDataBrief(value):
  return getWordProcessingData(value, False)
def getWordProcessingData(value, isList=True):
  outValue = " ".join(value)
  if isList:
    outValue = "<pre>\n" + cgi.escape(outValue) + "\n</pre>\n"
  return outValue

"""
"""
rpc_list_fields = (('.01', getRPCHRefLink), # Name
                   ('.02', None), # Tag
                   ('.03', getRoutineHRefLink), # Routine
                   ('.05', None),# Availability
                   ('1', getWordProcessingDataBrief),# Description
                   )

def writeRPCTableInfo(output):
  #output.write("<table id=\"rpctable\" class=\"tablesorter\">\n")
  output.write("<div id=\"demo\">")
  output.write("<table id=\"rpctable\" class=\"display\">\n")
  output.write("<thead>\n")
  output.write("<tr>\n")
  for name in ("Name", "Tag", "Routine", "Availability", "Description"):
    output.write("<th>%s</th>\n" % name)
  output.write("</tr>\n")
  output.write("</thead>\n")

def writeTableListInfo(output):
  #output.write("<table id=\"rpctable\" class=\"tablesorter\">\n")
  output.write("<div id=\"demo\">")
  output.write("<table id=\"rpctable\" class=\"display\">\n")
  output.write("<thead>\n")
  output.write("<tr>\n")
  for name in ("Name", "IEN"):
    output.write("<th>%s</th>\n" % name)
  output.write("</tr>\n")
  output.write("</thead>\n")

def generateRPCListHtml(dataEntryLst, outputName, dir):
  """
    Specific logic to handle RPC List
    @TODO move the logic to a specific file
  """
  with open("%s/%s.html" % (dir, outputName), 'w+') as output:
      output.write("<html>\n")
      output.write("%s\n" % dthead)
      output.write("<body id=\"dt_example\">")
      output.write("""<div id="container" style="width:80%">""")
      output.write("<h1>Package: %s RPC List</h1>" % (getPackageHRefLink(outputName)))
      writeRPCTableInfo(output)
      """ table body """
      output.write("<tbody>\n")
      for dataEntry in dataEntryLst:
        tableRow = [""]*len(rpc_list_fields)
        allFields = dataEntry.fields
        output.write("<tr>\n")
        for idx, id in enumerate(rpc_list_fields):
          if id[0] in allFields:
            value = allFields[id[0]].value
            if id[1]:
              value = id[1](value)
            tableRow[idx] = value
        for item in tableRow:
          output.write("<td class=\"ellipsis\">%s</td>\n" % item)
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

def getDataEntryHtmlFile(dataEntry, ien, fileNo):
  entryName = str(dataEntry.name)
  return getDataEntryHtmlFileByName(entryName, ien, fileNo)

def getDataEntryHtmlFileByName(entryName, ien, fileNo):
  entryName = entryName[:20] # max 20 chars
  return safeFileName("%s-%s-%s" % (fileNo, ien, entryName)) + ".html"

def generateDataTableHtml(fileManData, fileNo, dir):
  with open("%s/%s.html" % (dir, fileNo), 'w') as output:
    output.write("<html>\n")
    output.write("%s\n" % dthead)
    output.write("<body id=\"dt_example\">")
    output.write("""<div id="container" style="width:80%">""")
    output.write("<h1>File %s Data List</h1>" % (fileNo))
    writeTableListInfo(output)
    output.write("<tbody>\n")
    for ien in getKeys(fileManData.dataEntries.keys(), float):
      dataEntry = fileManData.dataEntries[ien]
      if not dataEntry.name:
        logging.info("no name for %s" % dataEntry)
        continue
      dataHtmlLink = "<a href=\"%s\">%s</a>" % (getDataEntryHtmlFile(dataEntry, ien, fileNo),
                                                dataEntry.name)
      tableRow = [dataHtmlLink, dataEntry.ien]
      output.write("<tr>\n")
      """ table body """
      for item in tableRow:
        output.write("<td class=\"ellipsis\">%s</td>\n" % item)
      output.write("</tr>\n")
    output.write("</tbody>\n")
    output.write("</table>\n")
    output.write("</div>\n")
    output.write("</div>\n")
    output.write ("</body></html>\n")

def convertFileManDataToHtml(fileManData, dir):
  for ien in getKeys(fileManData.dataEntries.keys(), float):
    dataEntry = fileManData.dataEntries[ien]
    if not dataEntry.name:
      logging.info("no name for %s" % dataEntry)
      continue
    outHtmlFileName = getDataEntryHtmlFile(dataEntry, ien, fileManData.fileNo)
    with open("%s/%s" % (dir, outHtmlFileName), 'w') as output:
      output.write ("<html>")
      output.write ("%s\n" % dthead_rpc)
      output.write("<body id=\"dt_example\">")
      output.write("""<div id="container" style="width:80%">""")
      output.write ("<h1>%s (%s)</h1>\n" % (dataEntry.name, ien))
      outputFileEntryTableList(output)
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

import cgi
def fileManDataEntryToHtml(output, dataEntry, isRoot):
  if not isRoot:
    output.write ("<li>\n")
  for fldId in sorted(dataEntry.fields.keys(), key=lambda x: float(x)):
    if isRoot:
      output.write ("<tr>\n")
    dataField = dataEntry.fields[fldId]
    fieldType = dataField.type
    name, value = dataField.name, dataField.value
    """ hack for RPC """
    if isRoot and fldId == '.03' and dataField.name == "ROUTINE":
      value = getRoutineHRefLink(value)
    elif fieldType == FileManField.FIELD_TYPE_SUBFILE_POINTER:
      if value and value.dataEntries:
        if isRoot:
          output.write("<td>%s</td>\n" % name)
          output.write("<td>\n")
        else:
          output.write ("<dl><dt>%s:</dt>\n" % name)
          output.write ("<dd>\n")
        convertFileManSubFileDataToHtml(output, value)
        if isRoot:
          output.write("</td>\n")
        else:
          output.write ("</dd></dl>\n")
      continue
    elif fieldType == FileManField.FIELD_TYPE_FILE_POINTER:
      if value:
        fields = value.split(';')
        if len(fields) == 3: # fileNo, ien, name
          refFile = getDataEntryHtmlFileByName(fields[2], fields[1], fields[0])
          value = '<a href="%s">%s<a>' % (refFile, fields[-1])
        elif len(fields) == 2:
          value = 'File: %s, IEN: %s' % (fields[0], fields[1])
        else:
          logging.error("Unknown File Pointer Value %s" % dataField.value)
    elif fieldType == FileManField.FIELD_TYPE_WORD_PROCESSING:
      value = "\n".join(value)
      value = "<pre>\n" + cgi.escape(value) + "\n</pre>\n"
    if isRoot:
      output.write ("<td>%s</td>\n" % name)
      output.write ("<td>%s</td>\n" % value)
      output.write ("</tr>\n")
    else:
      output.write ("<dt>%s:  &nbsp;&nbsp;%s</dt>\n" % (name, value))
      #output.write ("<dd>%s</dd>\n" % value)
  if not isRoot:
    output.write("</li>\n")

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
    generateDataTableHtml(fileManData, fileNo, outDir)
    convertFileManDataToHtml(fileManData, outDir)
