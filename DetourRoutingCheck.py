#!/bin/env python3.7

import os
import re
import sys
import glob
import time
import shutil
import signal
import subprocess

def Interrupt( siignal_received, frame ):

  print( "" )

  jobs = glob.glob( "job.id" )

  write = open( "interrput.log", "w" )

  for job in jobs:

    read = open( job, "r" )

    for line in read.readlines():
      matchObjects = re.match( r'\s*Job\s+<(\S+)>\s+is\s+submitted\s+to\s+queue\s+<(\S+)>.$', line )

      if matchObjects:
        id = matchObjects.group( 1 )
        queue = matchObjects.group( 2 )
        print( "[WARNING] Kill job %s from queue <%s>" % ( id, queue ) )
        command = "bkill"
        command += " " + id
        subprocess.call( command, shell = True, stdout = write, stderr = write )

    read.close()

  write.close()

  exit( -1 )

def Init( setup ):

  if not os.path.exists( "user_setup" ):
    shutil.copy( rootDir + "user_setup", "user_setup" )
    command = "vim user_setup"
    subprocess.call( command, shell = True, stdout = None, stderr = None )

  read = open( "user_setup", "r" )

  for line in read.readlines():
    matchObjects = re.match( r'^\s*(\S+)\s+=\s+((?!#)[\w"\/\*\s+\.]*)', line )

    if matchObjects:
      variable = matchObjects.group( 1 )
      value = re.sub( "\"", "", matchObjects.group( 2 ) ).split()

      if len( value ) == 0:
        setup[ variable ] = ""
      elif len( value ) == 1:
        setup[ variable ] = value[ 0 ]
      else:
        setup[ variable ] = value

  read.close()

  setup[ "ROOT" ] = os.getcwd()
  setup[ "PERC_ROOT" ] = rootDir + "calibrePERC.top"
  setup[ "CALIBRE_VERSION" ] = "2020.1_36.18"

  return True

def InputCheck( setup ):

  checkItems = [  "PROCESS", \
                  "PROJECT", \
                  "VERSION", \
                  "NETS", \
                  "GDS_PATH", \
                  "GDS_TOP" \
                ]
 
  for checkItem in checkItems:
    if setup[ checkItem ] == "":
      print( "[ERROR] %s is empty" % ( checkItem ) )
      print( "        Please check the variable \"%s\" in your user_setup file" % ( checkItem ) )
      return False

  checkItems = [ "SPICE_PATH", \
                 "SPICE_TOP" \
               ]

  if not os.path.exists( setup[ "NXF" ] ):
    for checkItem in checkItems:
      if setup[ checkItem ] == "":
        print( "[ERROR] %s is empty" % ( checkItem ) )
        return False

  checkPaths = [ "GDS_PATH", \
                 "SPICE_PATH", \
               ]

  for checkPath in checkPaths:
    if not os.path.exists( setup[ checkPath ] ):
      print( "[ERROR] %s file path \"%s\" doesn't exist" % ( checkPath, setup[ checkPath ] ) )
      return False

  return True

def LVSDeckCentralPathCheck( path ):
  if not os.path.exists( path ):
    print( "[ERROR] Wrong PROJECT or VERSION or RUNSET_PATH" )
    return False
  return True

def Abort():
  print( "[ERROR] Detour Routing Check Terminated Abnormally" )
  exit( -1 )

def CreateNXF( setup ):

  command = ""

  if not os.path.exists( setup[ "NXF" ] ):

    #print( "[INFO] No nxf file" )
    print( "[INFO] Starting LVS" )

    if not os.path.exists( "LVS" ):
      os.mkdir( "LVS" )

    os.chdir( "LVS" )

    command = "rm -rf DONE && "
    command += rootDir + "RunCalibre.py"
    command += " -lvsDeck \"" + setup[ "LVS_ROOT" ] + "\""
    command += " -spicePath \"" + setup[ "SPICE_PATH" ] + "\""
    command += " -spiceTop \"" + setup[ "SPICE_TOP" ] + "\""
    command += " -gdsPath \"" + setup[ "GDS_PATH" ] + "\""
    command += " -gdsTop \"" + setup[ "GDS_TOP" ] + "\""
    command += " -options -nxf"
    command += " -switchOn LVS_NOT_ABORT"
    command += " -noRun"

    if setup[ "ENABLE_VIRTUAL_CONNECTION" ]:
      command += " -code \"VIRTUAL CONNECT COLON YES\""
      command += " -code \"VIRTUAL CONNECT NAME ?\""

    command += " && bsub -q lvs run.csh"

    writeOut = open( "job.id", "w" )
    writeErr = open( "error", "w" )

    subprocess.call( command, shell = True, stdout = writeOut, stderr = writeErr )

    writeOut.close()
    writeErr.close()

    while not os.path.exists( "DONE" ):
      time.sleep( 5 )

    setup[ "NXF" ] = setup[ "ROOT" ] + "/LVS/svdb/" + setup[ "SPICE_TOP" ] + ".nxf"

    os.chdir( "../" )

  return True

def PreProcessLVSDeck( path ):

  read = open( path, "r" )
  write = open( "calibreLVS.rule", "w" )

  for line in read.readlines():
    if re.match( r'^\s*(LAYOUT|SOURCE)\s+(PATH|PRIMARY|SYSTEM)', line ):
      line = "//" + line
    elif re.match( r'^\s*MASK\s+SVDB\s+DIRECTORY', line ):
      line = "//" + line
    elif re.match( r'\s*(\/\/)?\s*#DEFINE\s+LVS_NOT_ABORT', line ):
      line = "#DEFINE LVS_NOT_ABORT" + "\n"

    write.write( line )

  read.close()
  write.close()

def RunPERC( setup ):

  print( "[INFO] Starting PERC", flush = True )

  switches = [ "ENABLE_VIRTUAL_CONNECTION", \
               "ENABLE_LAYOUT_TEXT_FILE", \
               "ENABLE_TOP_ONLY", \
               "ENABLE_INCLUDE_PORT", \
               "ENABLE_BBOX_METHODOLOGY" \
             ]

  variables = [ "PHYSICAL_WIRELENGTH_THRESHOLD", \
                "MIN_PHYSICAL_WIRELENGTH", \
                "LOWER_LAYER", \
                "UPPER_LAYER", \
                "CHECK_CELL_WITH_LAYOUT_VIEW", \
                "NXF", \
                "NETS", \
                "TEXT" \
              ]

  if "PROCESS" in setup:
    ENABLE_PROCESS = setup[ "PROCESS" ]
    setup[ ENABLE_PROCESS ] = "1"
    switches.append(ENABLE_PROCESS)

  if not os.path.exists( "PERC" ):
    os.mkdir( "PERC" )

  os.chdir( "PERC" )

  PreProcessLVSDeck( setup[ "LVS_ROOT" ] )

  command = "rm -rf DONE && "
  command += rootDir + "RunCalibre.py"
  command += " -version \"" + setup[ "CALIBRE_VERSION" ] + "\""
  command += " -percDeck " + rootDir + "calibrePERC.top"
  command += " -gdsPath \"" + setup[ "GDS_PATH" ] + "\""
  command += " -gdsTop \"" + setup[ "GDS_TOP" ] + "\""
  command += " -spicePath \"" + setup[ "SPICE_PATH" ] + "\""
  command += " -spiceTop \"" + setup[ "SPICE_TOP" ] + "\""
  command += " -noRun"
  command += " -switchOn"

  for switch in switches:
    if setup[ switch ] == "1":
      command += " " + switch

  command += " -switchOff"

  for switch in switches:
    if setup[ switch ] == "0":
      command += " " + switch

  for variable in variables:
    command += " -variable " + variable
    if type( setup[ variable ] ) == list:
      for value in setup[ variable ]:
        command += " \"" + value + "\""
    else:
       command += " \"" + str( setup[ variable ] ) + "\""

  command += " && bsub -q drc run.csh"

  writeOut = open( "job.id", "w" )
  writeErr = open( "error", "w" )

  subprocess.call( command, shell = True, stdout = writeOut, stderr = writeErr )
  print("My PID : ", os.getpid())

  writeOut.close()
  writeErr.close()

  while not os.path.exists( "DONE" ):
    time.sleep( 5 )

  # write = open( "test.log", "w" )

  # command = rootDir + "test.tcl " + setup[ "NETS" ] + " nxf > drc.rdb"

  # subprocess.call( command, shell = True, stdout = write, stderr = write )

  # write.close()

  os.chdir( "../" )

  return True

if __name__ == "__main__":

  signal.signal( signal.SIGINT, Interrupt )
  
  rootDir = "/apps/imctf/cad/script/DetourRoutingCheck/"

  setup = dict()

  Init( setup )
  
  if not InputCheck( setup ):
    Abort()

  if setup[ "RUNSET_PATH" ]:
    setup[ "LVS_ROOT" ] = setup[ "RUNSET_PATH" ] + "/current/calibreLVS.rule"  
  else:
    setup[ "LVS_ROOT" ] = "/apps/imctf/cad/runset/" + setup[ "PROJECT" ].lower() + "/" + setup[ "VERSION" ].lower() + "/current/calibreLVS.rule"
  print("RUNSET:"+setup[ "LVS_ROOT" ])
  if not LVSDeckCentralPathCheck( setup[ "LVS_ROOT" ] ):
    Abort()

  #CreateNXF( setup )
  RunPERC( setup )

  print( "[INFO] Detour Routing Check Done" )
  print( "[INFO] Please use Calibre %s or above version to review the result" % ( setup[ "CALIBRE_VERSION" ] ) )
  print( "       Virtuoso Layout Suit L -> Calibre (Manu Bar) -> StartRVE -> Database (" + setup[ "ROOT" ] + "/PERC/dfmdb) -> Database Type (PERC) -> Open" )
  
  exit( 0 )
