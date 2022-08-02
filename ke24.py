#!/usr/bin/python3
# vim: set ts=3 sw=3 et :

version = '2.0'
#debug = True
debug = False

import sys, getopt, serial
import os
import yaml
import traceback
from pathlib import Path

#debug
import pprint
#/debug

quiet_override = False
cfgpaths = ['~/.config/ke24.conf', '/etc/ke24.conf']
config = []
ke24 = {}
actions = []

# Dictionaries to address the relays and gpios by
# their respective names or by their controlling device
devices = {}
relays = {}
gpios = {}

def printHelp(rc = 0, argv = ['ke24.py']):
   print('Usage:')
   print('\t%s [<options>]\n' % argv[0])
   print('Options:')
   print('\t-h|--help             - Print this help')
   print('\t-q|--quiet            - Quiet mode. Only the necessary output.')
   print('\t-v|--verbose          - Verbose mode. All output.')
   print('\t-c|--config <file>    - Specify config file location')
   print('\t-d|--device <name>    - Operate on device with the given name')
   print('\t-r|--relay <name|idx> - Operate on relay with index <idx>\n'
        +'\t                        or on relay with the given <name>')
   print('\t-o|--gpio <name|idx>  - Operate on GPIO line number <index>')
   print('\t-s|--set <name|value> - Change operation to "set" from the default "get",\n'
        +'\t                        set the device selected with -r or -o to new\n'
        +'\t                        numeric <value> or to the named value with\n'
        +'\t                        the given <name>')
   sys.exit(rc)

def parseargs(argv):
   global cfgpaths
   global quiet
   global quiet_override

   try:
      opts, args = getopt.getopt(argv[1:],
                                 "hqvc:r:o:s:d:",
                                 ["help", "quiet", "verbose",
                                  "config=","device=","relay=","gpio=","set="])
   except getopt.GetoptError:
      printHelp(2, argv)

   for opt, arg in opts:
      # These options define actions and their targets
      if opt in ['-s', '--set',
                 '-r', '--relay',
                 '-o', '--gpio']:

         # For each new option fetch the last action
         # to allow for the argument to update it.
         # If there are no previous actions, prepare
         # an empty one, default to unspecified device.
         device = ''
         if len(actions) > 0:
            action = actions.pop()
            # The -d option affects all the subsequent
            # options, so fetch the last specified device.
            try:
               device = action['device']
            except Exception:
               pass
         else:
            action = {}

         # If the last action definition was complete,
         # and the option is not changing the operation,
         # push the action back to the list
         try:
            action['unit']
            if opt not in ['-s', '--set']:
               actions.append(action)
               action = {}
         except Exception:
            pass

      if opt in ['-h', "--help"]:
         printHelp(0, argv)
      elif opt in ["-q", "--quiet"]:
         if quiet_override:
            raise RuntimeError("Don't specify both -q and -v")
         quiet = True
         quiet_override = True
      elif opt in ["-v", "--verbose"]:
         if quiet_override:
            raise RuntimeError("Don't specify both -q and -v")
         quiet = False
         quiet_override = True
      elif opt in ["-d", "--device"]:
         # The device always denotes a new action
         actions.append({ 'device': arg })
      elif opt in ["-r", "--relay"]:
         # Add a new unit action entry, default to 'Get' operation
         action.update({
            'device': device,
            'unit'  : 'Relay',
            'index' : arg,
            'operation': 'Get',
            'value' : 0
         })
         actions.append(action)
      elif opt in ["-o", "--gpio"]:
         # Add a new unit action entry, default to 'Get' operation
         action.update({
            'device': device,
            'unit'  : 'GPIO',
            'index' : arg,
            'operation': 'Get',
            'value' : 0
         })
         actions.append(action)
      elif opt in ["-s", "--set"]:
         # Change the last operation to 'Set'
         if not action:
            raise RuntimeError("Must use -r or -o before -s")
         action.update({'operation' : 'Set', 'value' : arg})
         actions.append(action)
      elif opt in ["-c", "--config"]:
         cfgpaths.insert(0, arg);

def loadconfig(cfgpaths):
   config = {}
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

         return config

   raise RuntimeError("Configuration file not found: %s" % cfgpaths)

def parseconfig(config):
   devices = {}
   relaymap = {}
   gpiomap = {}
   # Bind named 'devices' to physical ports by serial numbers
   for port in config['Ports']:
      name = list(port.keys())[0]
      speed = port[name] or 115200
      if not quiet: print("Found port %s, speed %s" % (name, speed))
      if not Path.is_char_device(Path(name)):
        if not quiet: print("  The port is not a character device")
        continue
      for dev in config['Devices']:
         devname = list(dev.keys())[0]
         dev['name'] = devname
         if not quiet: print("  Checking for device '%s' ..." % devname)
         dev['ke'] = Ke24(name, speed)

         try:
            sn = dev['serial']
         except Exception:
            print(dev)
            raise RuntimeError("No 'serial' is defined for %s" % name)

         if not quiet: print('    S/N: %s ' % sn, end='')
         if sn != dev['ke'].serial():
            if not quiet: print('NOT FOUND')
            continue

         ver = dev['ke'].ver()
         if not quiet: print('')
         if ver != [2, 0]:
            if not quiet:
               raise RuntimeError ('Unsupported firmware version %s'
                                  % '.'.join(str(v) for v in ver))

         try:
            relays = dev['relays']
         except Exception:
            relays = {}
            dev['relays'] = relays

         dev['relaymap'] = {}

         for rel in relays:
            try:
               idx = rel['index']
            except Exception:
               raise RuntimeError("The 'index' field is missing for a relay")

            rel['type'] = 'Relay'
            relname = ''
            defstate = ''
            states = {}
            try:
               relname = rel['name']
               states = rel['states']
               defstate = rel['default']
            except Exception:
               pass

            # Allow to map gpios by name
            dev['relaymap'][idx] = rel
            rel['device'] = dev
            if relname:
               dev['relaymap'][relname] = rel
               # Allow for mapping relays by name globally
               try:
                 relaymap[relname]
               except Exception:
                 relaymap[relname] = []
               relaymap[relname].append(rel)

            if debug:
               print("    Relay %s %s %s" %
                    (rel['index'],
                     ('"%s"' % relname) if relname else '',
                     ('(default: %s)' % defstate) if defstate else ''))

         try:
            gpios = dev['gpio']
         except Exception:
            gpios = {}
            dev['gpio'] = gpios

         dev['gpiomap'] = {}

         for gpio in gpios:
            try:
               idx = gpio['index']
            except Exception:
               raise RuntimeError("The 'index' field is missing for a gpio line")

            gpio['type'] = 'GPIO'
            gpioname = ''
            defstate = ''
            states = {}
            try:
               gpioname = gpio['name']
               states = gpio['states']
               defstate = gpio['default']
            except Exception:
               pass

            # Allow to map gpios by index and name
            dev['gpiomap'][idx] = gpio
            gpio['device'] = dev
            if gpioname:
               dev['gpiomap'][gpioname] = gpio
               # Allow for mapping gpios by name globally
               try:
                 gpiomap[gpioname]
               except Exception:
                 gpiomap[gpioname] = []
               gpiomap[gpioname].append(gpio)

            if debug:
               print("    GPIO %s %s %s" %
                    (gpio['index'],
                     ('"%s"' % gpioname) if gpioname else '',
                     ('(default: %s)' % defstate) if defstate else ''))

         devices[devname] = dev

   return (devices, relaymap, gpiomap)

class Ke24:
   """A class implementing the Ke-USB24R device interface"""

   maxindex = {
      'Relay' : 4,
      'GPIO'  : 18
   }

   def __init__(self, port, baud):
      self.port = serial.Serial(port, baudrate = baud, timeout = 0.100)

   def cmd(self, command):
      prefix = command.split(',')[0]
      realcmd = "$KE,%s\r\n" % command
      self.port.write(realcmd.encode())
      # Chomp off the \r\n and split the response by comma
      response = self.port.read(256).decode()[:-2].split(',')
      # Response to a command always starts with
      # a '#' followed by the command name
      if response[0] != '#%s' % prefix:
         raise RuntimeError("Command '%s' wrong response: %s vs. %s" % (realcmd, response, '#%s' % prefix))
      return response[1:]

   def ver(self):
      return [int(i) for i in self.cmd('FW')[0].split('.')]

   def serial(self):
      return self.cmd('SER')[0]

   def get_relay(self, line):
      state = self.cmd('RDR,%s' % line)
      if int(state[0]) != int(line):
         raise RuntimeError('Response for wrong relay [%s vs. %s]' % (state[0], line))
      return int(state[1])

   def set_relay(self, line, val):
      response = self.cmd('REL,%s,%s' % (line, val))
      if response[0] != 'OK':
         raise RuntimeError(response)
   ##
   # @brief Set GPIO line direction
   # @param line       GPIO line number
   # @param direction  Direction to set ('IN' or 'OUT')
   # @param save       Save in NVRAM ? A boolean flag
   #
   def set_dir(self, line, direction, save = False):
      realdir = '1' if direction == 'IN' else '0'
      response = self.cmd('IO,SET,%s,%s%s' % (line, realdir, ',S' if save else ''))
      if response != [ 'SET', 'OK' ]:
         raise RuntimeError(response)

   def read(self, line):
      response = self.cmd('RD,%s' % line)
      if response[0] != '%02d' % int(line):
         raise RuntimeError('Wrong line in response: %s vs. %s' % (response[0], line))
      return int(response[1])

   def operation(self, opname, unit, index, arg = 0):
      value = -1
      if operation == 'Get':
         if unit == 'Relay':
            op = self.get_relay
         else:
            op = self.read
            self.set_dir(index, 'IN')
         value = op(index)
      elif operation == 'Set':
         if unit == 'Relay':
            op = self.set_relay
         else:
            raise RuntimeError('Setting GPIO is not supported yet')
         op(index, arg)
      else:
         raise RuntimeError(f"Program error. Wrong operation '{operation}' encountered.")
      return value

def find_device(target):
   for dev in devices:
      print(dev)

####### Main program start here

parseargs(sys.argv)

if len(actions) == 0:
   printHelp(0, sys.argv)

try:
   # If the mode wasn't set by command line options,
   # default to verbose
   try:
      quiet
   except Exception:
      quiet = False

   config = loadconfig(cfgpaths)
   if not config:
      print("No config files found")
      sys.exit(1)

   if not quiet_override:
      try:
         mode = config['Mode']
      except Exception:
         mode = 'Verbose'

      quiet = True if mode == 'Quiet' else False

   (devices, relays, gpios) = parseconfig(config)

   if debug:
      pp = pprint.PrettyPrinter(indent=1, depth=10)
      pp.pprint(devices)
      pp.pprint(relays)
      pp.pprint(gpios)

except Exception as e:
#  raise SystemExit(e)
   print(f"FAIL: {e}")
#   traceback.print_exc()
   sys.exit(1)

if debug:
   pp = pprint.PrettyPrinter(indent=1, depth=10)
   pp.pprint(actions)

for action in actions:
   devname = action['device']
   unitname = action['unit']
   idxname = action['index']
   operation = action['operation']
   valname = action['value']
   is_numeric = False
   device = {}

   if devname:
      try:
         device = devices[devname]
      except Exception:
         print(f"Device '{devname}' is not defined")
         sys.exit(1)

   try:
      # Check if the unit is specified as a numeric index
      if int(idxname) < 1 or int(idxname) > Ke24.maxindex[unitname]:
         print(f"{unitname} index {idxname} is out of range [1..{Ke24.maxindex[unitname]}]")
         sys.exit(1)
      is_numeric = True
   except Exception:
      # Must be a name, we're ok with that so far
      pass

   # Now find the unit
   if unitname == 'Relay':
      units = relays
   else:
      units = gpios

   try:
      unitcount = len(units[idxname])
   except Exception:
      unitcount = 0

   if not is_numeric and unitcount == 0:
      print(f"Could not find {unitname} '{idxname}' anywhere in configuration")
      sys.exit(1)

   unit = {}
   if unitcount > 1 and not device:
      print(f"{unitname} '{idxname}' is defined for multiple devices, use -d to clarify")
      sys.exit(1)
   elif unitcount > 1:
      # The unit name is defined multiple times, but device name is specified.
      # Find the implied unit using device name matching.
      for u in units[idxname]:
         if u['device']['name'] == devname:
            unit = u
            break
   else:
      # The unit name is present in just a single device or is numeric
      unit = {}
      if not is_numeric:
        unit = units[idxname]
      else:
        if not device and len(devices) == 1:
           device = devices[list(devices.keys())[0]]

        if device:
           unit.update({ 'device' : device })
        else:
           print(f"More than 1 device is defined, can't assume the target for {unitname} {idxname}")
           sys.exit(1)

        unit.update({
           'type' : unitname,
           'index' : idxname
        })

   value = -1
   if operation == 'Set':
      try:
         value = int(valname)
         # The valname is numeric, check sanity
         if value not in [0, 1]:
            print("Numeric value to set is invalid. Must be 1 or 0.")
            sys.exit(1)
      except Exception as e:
         # Must be a name, check if it is defined for the unit
         try:
            value = unit['states'][valname]
            if value not in [0, 1]:
               print(f"Value for state '{valname}' is invalid, must be 1 or 0.")
               sys.exit(1)
         except Exception:
            print(f"The value for state '{valname}' is not defined in configuration.")
            sys.exit(1)

   if not quiet:
      print ("%sing %s '%s' (%d) value%s" %
            (operation, unitname, idxname, unit['index'], f" to '{valname}' ({value})" if operation == 'Set' else ''))

   value = unit['device']['ke'].operation(operation, unit['type'], unit['index'], value)

   if operation == 'Get':
      valname = ''

      try:
         for state in list(unit['states'].keys()):
            if unit['states'][state] == value:
               valname = state
               break
      except Exception:
         # There are no named states defined for the unit
         pass

      if not quiet:
         print("%s '%s' = %d%s" % (unitname, idxname, int(value), ' ({valname})' if valname else ''))
      else:
         print("%s%s" % (value, f' {valname}' if valname else ''))
