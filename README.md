Copyright (C) 2022, KNS Group LLC («YADRO»).
All rights reserved

SPDX-License-Identifier: GPL-2.0-or-later

Author: Alexander Amelkin <alexander@amelkin.msk.ru>

**KE24** 

This is a Python program to control the [KernelChip KE-USB24R][1] relay module.

Currently, the program supports the following operations:

  - Reading a relay state
  - Reading a GPIO line state
  - Setting a GPIO line output value
  - Setting a relay state
  - Reading firmware version

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

-r | --relay <index> - Operate on the given relay. Default operation is to get the state.

-o | --gpio <index> - Operate on the given GPIO line. Default operation is to read the value.
                      Switches the given GPIO line into input mode.

-s | --set <value> - Set the state/value of the preceding device to the given value

The `-r`, `-o`, and `-s` options can be specified multiple times. Each `-r` or `-o` option defines a new
operation to be performed in sequence. The `-s` option modifies the last specified operation. For example, the following command:

`ke24.py -q -r 1 -r 3 -o 18`

will read the state of relays 1 and 3, switch GPIO line 18 into input mode and read it's value,
then print all those data one per line without any extra decoration, like this:

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

***Configuration***

Currently, the configuration can only be set via a yaml file.

Check [ke24.conf] for the configuration example.
By default the program looks for a configuration file at the following locations:

  - `/etc/config/ke24.conf`
  - `~/.config/ke24.conf`

You may specify an alternate configuratin file using the `-c|--config <path>` option.


