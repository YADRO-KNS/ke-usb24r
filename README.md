Copyright (C) 2022, KNS Group LLC («YADRO»).
All rights reserved

SPDX-License-Identifier: GPL-2.0-or-later

Author: Alexander Amelkin <alexander@amelkin.msk.ru>

**KE24**

This is a Python program to control the KernelChip KE24USB relay module.
More information about the module can be found at [https://kernelchip.ru/Ke-USB24R.php].

Currently, the program doesn't do much and can be invoked like this:

```
$ ./ke24.py -c myconfig.yaml
```

Check [example.yaml] for the configuration example.
By default the program looks for a configuration file at the following locations:

  * `/etc/config/ke24.conf`
  * `~/.config/ke24.conf`

