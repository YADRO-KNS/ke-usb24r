#!/usr/bin/python3
# vim: set ts=3 sw=3 et :

import sys, getopt, serial
import os
import yaml
import traceback
from pathlib import Path

quiet = False
cfgpaths = ['~/.config/ke24.conf', '/etc/ke24.conf']
config = []
ke24 = {}
actions = []

def printHelp(rc = 0, argv = ['ke24.py']):
   print('Usage:')
   print('\t%s [<options>]\n' % argv[0])
   print('Options:')
   print('\t-h|--help          - Print this help')
   print('\t-q|--quiet         - Quiet operation. Only the necessary output.')
   print('\t-c|--config <file> - Specify config file location')
   print('\t-r|--relay <index> - Operate on relay number <index>')
   print('\t-o|--gpio <index>  - Operate on GPIO line number <index>')
   print('\t-s|--set <value>   - Change operation to "set" from the default "get",\n'
        +'\t                     set the device selected with -r or -o to new\n'
        +'\t                     value <value>.')
   sys.exit(rc)

def parseargs(argv):
   global cfgpaths

   try:
      opts, args = getopt.getopt(argv[1:],
                                 "hqc:r:o:s:",
                                 ["help", "quiet", "config=","relay=","gpio=","set="])
   except getopt.GetoptError:
      printHelp(2, argv)

   for opt, arg in opts:
      if opt in ['-h', "--help"]:
         printHelp(0, argv)
      elif opt in ["-q", "--quiet"]:
         global quiet
         quiet = True
      elif opt in ["-r", "--relay"]:
         relay = int(arg)
         if relay < 1 or relay > 4:
            raise RuntimeError("Relay index %d is out of range [1..4]" % relay)
         # Add a new device action entry, default to 'Get' action
         device = ['Relay', relay]
         action = ['Get', 0]
         actions.append([device, action])
      elif opt in ["-o", "--gpio"]:
         gpio = int(arg)
         if gpio < 1 or gpio > 18:
            raise RuntimeError("GPIO index %d is out of range [1..18]" % relay)
         # Add a new device action entry, default to 'Get' action
         device = ['GPIO', gpio]
         action = ['Get', 0]
         actions.append([device, action])
      elif opt in ["-s", "--set"]:
         val = int(arg)
         if val != 1 and val != 0:
            raise RuntimeError("Value to set is invalid. Must be 1 or 0." % relay)
         # Replace the last action with 'Set'
         if len(actions) < 1:
            raise RuntimeError("Must use -r or -o before -s")
         action = actions.pop()
         action[1] = ['Set', val]
         actions.append(action)
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
   global ke24
   port = config['Serial']['Port']
   baud = config['Serial']['Speed']
   ke24 = serial.Serial(port, baudrate = baud, timeout = 0.250)

def ke24_cmd(cmd):
   prefix = cmd.split(',')[0]
   realcmd = "$KE,%s\r\n" % cmd
   ke24.write(realcmd.encode())
   response = ke24.read(256).decode()[:-2].split(',')
   if response[0] != '#%s' % prefix:
      raise RuntimeError("Command '%s' wrong response: %s vs. %s" % (realcmd, response, '#%s' % prefix))
   return response[1:]

def ke24_ver():
   ver = []
   return [int(i) for i in ke24_cmd('FW')[0].split('.')]

def ke24_get_relay(line):
   state = ke24_cmd('RDR,%s' % line)
   if int(state[0]) != int(line):
      raise RuntimeError('Response for wrong relay [%s vs. %s]' % (state[0], line))
   return int(state[1])

def ke24_set_relay(line, val):
   response = ke24_cmd('REL,%s,%s' % (line, val))
   if response[0] != 'OK':
      raise RuntimeError(response)
##
# @brief Set GPIO line direction
# @param line       GPIO line number
# @param direction  Direction to set ('IN' or 'OUT')
# @param save       Save in NVRAM ? A boolean flag
#
def ke24_set_dir(line, direction, save = False):
   realdir = '1' if direction == 'IN' else '0'
   response = ke24_cmd('IO,SET,%s,%s%s' % (line, realdir, ',S' if save else ''))
   if response != [ 'SET', 'OK' ]:
      raise RuntimeError(response)

def ke24_read(line):
   response = ke24_cmd('RD,%s' % line)
   if response[0] != '%02d' % int(line):
      raise RuntimeError('Wrong line in response: %s vs. %s' % (response[0], line))
   return int(response[1])

####### Main program start here

#if __name__ == "__main__":
parseargs(sys.argv)

if len(actions) == 0:
   printHelp(0, sys.argv)

try:
   config = loadconfig(cfgpaths)
   ke24_open()
   ver = ke24_ver()
except Exception as e:
   print("FAIL: %s" % e)
   traceback.print_exc()
   sys.exit(1)

if ver != [2, 0]:
   print ('Unsupported firmware version %s' % '.'.join(str(v) for v in ver))
   sys.exit(1)


for action in actions:
   operation = action[1][0]
   value = action[1][1]
   device = action[0][0]
   index = action[0][1]

   if not quiet:
      print ('%sing %s %s value%s' %
            (operation, device, index, (' to %s' % value) if operation == 'Set' else ''))
   if operation == 'Get':
      if device == 'Relay':
         value = ke24_get_relay(index)
      elif device == 'GPIO':
         ke24_set_dir(index, 'IN')
         value = ke24_read(index)
      else:
         raise RuntimeError('Program error. Wrong device "%s" encountered.' % device)

      if not quiet:
         print('%s %s = %s' % (device, index, value))
      else:
         print(value)

   elif operation == 'Set':
      if device == 'Relay':
         ke24_set_relay(index, value)
      elif device == 'GPIO':
         print('Setting GPIO is not supported yet')
         os.exit(1)
      else:
         raise RuntimeError('Program error. Wrong device "%s" encountered.' % device)
   else:
      raise RuntimeError('Program error. Wrong operation "%s" encountered.' % operation)

