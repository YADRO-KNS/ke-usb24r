Copyright (C) 2022, KNS Group LLC («YADRO»).
All rights reserved

SPDX-License-Identifier: GPL-2.0-or-later

Author: Alexander Amelkin <alexander@amelkin.msk.ru>

**KE24** 

***Introduction***

This is a Python program to control the [KernelChip KE-USB24R][1] relay module.

Currently, the program supports the following operations:

  - Reading a relay state
  - Reading a GPIO line state
  - Setting a GPIO line output value
  - Setting a relay state
  - Reading firmware version

The tool is quite versatile and can be easily configured to your needs
via a YAML file. One of the advantages is that you may define a list of
ttyACM ports to search for your Ke-USB24R modules using their serial numbers,
and then configure different "devices" to serve your needs.

Imagine that you're developing support for a chassis intrusion sensor, and
in your lab you have four devices called "athos", "porthos", "aramis" and
"dartagnan" with their chassis intrusion sensors connected to relays 1-4
of your Ke-USB24R module. You may then configure this tool to allow for
invocation like this:

```
$ ke24.py -d athos -r cover -s closed -d aramis -r cover -s open
```

The program will search for a device definition with name `athos` in
the configuration file (see below), take the serial number of Ke-USB24R,
search for the module among the listed ports (ttyACM\* devices), and then
use the device definition to set the named relay `cover` to the named
state `closed`. It will then repeat the operation for a device named `aramis`,
except that it will set its `cover` relay to the named state `open`.

Alternatively, you may just set up 1 device per Ke-USB24R module and use
raw numbers like this:

```
$ ke24.py -d main_module -r 2 -s 0
```

Or if you have just one module and one device defined for it, you may
even omit the `-d` option:

```
$ ke24.py -r 2 -s 0 -r 3 -s 1
```

[1]: https://kernelchip.ru/Ke-USB24R.php

***Installation***

Just put the program into your favourite path for the executables,
for example, `/usr/local/bin`, and make it executable:

```
$ cp ke24.py /usr/local/bin
$ chmod 755 /user/local/bin/ke24.py
```

***Usage***

Generally you use the program by running it like this:

```
$ ke24.py <options>
```

You may always check the help on the options by running: 

```
$ ke24.py --help 
```

***Options***

-h | --help - Show help

-c | --config <file> - Load configuration from the given file

-q | --quiet - Quiet operation, only the necessary output (like values of the requested relays and/or GPIO lines)

-d | --device <name> - Operate on the given device. Can be omitted if there is only one
                       device that matches the -r and/or -o options. Can be specified multiple
                       times if you want further options to apply to a different device.

-r | --relay <name|index> - Operate on the given relay. Default operation is to get the state.
                            See the config template for more info on names.

-o | --gpio <name|index> - Operate on the given GPIO line. Default operation is to read the value.
                           See the config template for more info on names.
                           Switches the given GPIO line into input mode.

-s | --set <name|value> - Set the state of the preceding device to the given value.
                          See the config template for more info on named values.

-I | --identify <port> - Read and print the serial number from the given port.
                         Return 0 if there was a Ke-USB24R there, return 1 otherwise.
			 Can be used with `udev` (see Installation above).

The `-d`, `-r`, `-o`, and `-s` options can be specified multiple times. Each
`-d` option designates a new device to which all the subsequent `-r` and `-o`
options will apply. Each `-r` or `-o` option defines a new operation to be
performed in sequence. The `-s` option modifies the last specified operation.
The devices are only specified by name, whereas relays and gpios may be
specified either by name or by index.  If you wish to specify the relays and/or
gpios by name, you must define them in the configuration file.  If you only
want to use indices, you may skip configuring them.

For example, if you have just a single Ke-USB24R module in your system, then
the following command will read the state of relays 1 and 3, switch GPIO line
18 into input mode and read it's value, then print all those data one per line
without any extra decoration, like this:

```
$ ke24.py -q -r 1 -r 3 -o 18
1
0
1
``` 

If you want to read relay 2, set relay 3 to 1, then read relay 4, use this:

```
$ ke24.py -q -r 2 -r 3 -s 1 -r 4
0
1
```

the relay set operation doesn't produce any output in quiet mode.

If you have defined any names for your devices and control units (relays and gpios),
then you may use them like this:

```
$ ke24.py -q -d Main -r Power -r Reset -d Watchdog -o "Kill switch"
1
0
1
```

Read the configuration template for more information on how to configure
names for your devices and control units.

***Configuration***

Currently, the configuration can only be set via a yaml file.

Check [ke24.conf] for the configuration example.
By default the program looks for a configuration file at the following locations:

  - `/etc/config/ke24.conf`
  - `~/.config/ke24.conf`

You may specify an alternate configuratin file using the `-c|--config <path>` option.

There is an example `ke24.conf` file provided with detailed comments.
