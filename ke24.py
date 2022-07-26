#!/usr/bin/python3
# vim: set ts=3 sw=3 et :

import sys, getopt, serial
import os
import yaml
from pathlib import Path

quiet = False
cfgpaths = ['~/.config/ke24.conf', '/etc/ke24.conf']
config = []
ke24 = {}

def parseargs(argv):
   global cfgpaths
   def printHelp(rc = 0):
      print('%s [-h|--help] [-q|--quiet] [-c|--config <file>]' % argv[0])
      sys.exit(rc)

   try:
      opts, args = getopt.getopt(argv[1:],"hqc:",["help", "quiet", "config="])
   except getopt.GetoptError:
      printHelp(2)

   for opt, arg in opts:
      if opt in ['-h', "--help"]:
         printHelp()
      elif opt in ["-q", "--quiet"]:
         global quiet
         quiet = True
      elif opt in ["-c", "--config"]:
         cfgpaths.insert(0, arg);

def loadconfig(cfgpaths):
   for cfg in cfgpaths:
      if not quiet:
         print("Looking for config in %s" % cfg)
      expcfg = os.path.expanduser(cfg)
      if os.path.isfile(expcfg):
         if not quiet:
            print("Loading config from %s" % cfg)
         with open(expcfg, 'r') as cfgfile:
            try:
               config = yaml.safe_load(cfgfile)
            except yaml.scanner.ScannerError as e:
               raise RuntimeError("Failed to load config: %s", e)

         try:
            port = config['Serial']['Port']
         except Exception:
            raise RuntimeError("No port defined in configuration")

         if not Path.is_char_device(Path(port)):
            raise RuntimeError("The port %s is not a character device"
                               % port)

         return config

   raise RuntimeError("Configuration file not found: %s" % cfgpaths)

def ke24_open():
   port = config['Serial']['Port']
   baud = config['Serial']['Speed']
   ke24 = serial.Serial(port, baud, timeout = 1)

####### Main program start here

#if __name__ == "__main__":
parseargs(sys.argv)

try:
   config = loadconfig(cfgpaths)
   ke24_open()
except Exception as e:
   print("FAIL: %s" % e)
   sys.exit(1)

#print(yaml.dump(config))
