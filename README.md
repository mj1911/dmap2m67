### THIS CODE IS CURRENTLY IN DEVELOPMENT and may be completely borked from time-to-time.

### img2m67 - Image to M67 GCODE

Python3/PyQt6 GUI app to convert an image to M67 Analog Output GCODE for PWM laser raster on LinuxCNC/Mesa hardware. 

Copyright (C) 2026  rdtsc/mj1911 and raggielyle.  Permission is granted to study and create derivative works, as long as this work is attributed.  However, forking, changing a few lines, and attempting to call this yours is prohibited.  If you just wish to add/fix/improve something, please send a pull request or PM (the LinuxCNC community is fragmented enough as it is.)  If you have any comments, can also try the LinuxCNC forums, IRC Libera #LinuxCNC, or Discord.

This app uses work from raggielyle, whom was kind enough to allow use of his conversion code and also helped test this version of it.  It is our hope that such a GUI can be used for more LinuxCNC tools in the future.

Here we use PyQt6 for the GUI.  The following dependencies must be installed prior:
1. PyQt6: Python bindings for the Qt6 toolkit.  Install this using your usual OS-install command, such as `sudo apt install python3-pyqt6 libxcb-cursor0`, `pamac install python-pyqt6`, `brew install pyqt6` etc.  Note I do not have a Mac to test.
2. Python Image Library (pillow): `sudo apt install python3-pil`, `pamac install python-pillow`, `brew install python3-pil` etc.

With those installed, this app should run.  It may give some error about 'dbus UnknownMethod' on some Linuxes, which means a missing `xdg-desktop-portal-*` package.  This is currently a rabbit-hole being avoided, as we do not need DBUS for this app.  Some versions of Python / PIL libary may also complain about getdata(), saying it is depreciated in favor of get_flattened_data().  These can be ignored for now.

Once running, the GUI first looks for saved settings.  If none, it creates defaults.  These settings are saved at close and loaded at start, so it "remembers" the last-used settings, including the last-opened image.

The GUI is just one screen, with controls on the left, and images on the right.  There is a minimum size of 1000x750 pixels (so will fit on a 1024x768 display), but it can be maximized to increase the size of the images (work-in-progress.)

The controls on the left allow you to select an image, adjust the conversion parameters, select an output gcode file, and perform the conversion.  

The images on the right include the original source image, the intermediate luma-converted-image, and a proposed rendering of the actual GCODE output, which is not working yet.  Luma ended up being a can-of-worms, as PIL luma mode is limited to 8 bits per pixel (range 0-255) but ideally we would want a much larger range than this.  A rework was attempted but reverted for now. It is hoped that armed with this tool, fewer failed jobs will result.

### Mesa / M67 Hardware

* Mesa Anything-IO cards which support a PWM output might require a different firmware to be loaded to do "real" PWM.  A card like the 7c80 has a spindle "pot" output, which is really a PWM output + RC filter + opamp.  Spindle outputs are far too slow for laser raster - a dedicated PWM output is required.  The 7c80 card has a "7c801p_5abobd.bit" firmware available, which changes step/dir channel 5 into a dedicated PWM output.  Such firmware needs loaded using the mesaflash utility.  The exact details vary depending on which card is being used.
* Once physical PWM output is covered, Mesa PWM outputs have higher resolution (14 bits? 0-8191) at lower frequences, and 12 bits (0-2047) up to 48kHz.  But to use a lower frequency, the travel speed must be reduced, so higher frequency is desirable.  
* Another consideration is that using more digits in the gcode makes the gcode file significantly larger, so fewer digits are desirable.  Therefore a compromise is using three digits for power, 0-999, which gives 1k intensity levels while still allowing 48kHz operation.  This is 3.92 times more resolution than the 255 levels afforded by hobby-grade lasers (assuming your laser can interpret the extra PWM detail.) 
* To make the link in HAL between Analog-out and the PWM, do something like `net  laser  motion.analog-out-01  ->  hm2_7c80.0.pwmgen.01.value`.  Note that on the 7c80 card, PWM 0 is the spindle, and PWM 1 is the dedicated PWM output on step/dir 5.  This may be similar or vastly different on other cards.
* To make the PWM output max-out at the chosen power value such as 999, do `setp  hm2_7c80.0.pwmgen.01.scale  999`.  To set the PWM frequency (globally) to 48kHz, do `setp  hm2_7c80.0.pwmgen.pwm_frequency  48000`.  To enable the PWM, do `setp  hm2_7c80.0.pwmgen.00.enable = true`.  May want to tie that to a GUI button, or some other safety measure, to enable/disable the laser.
* Note that since the 7c80 card has a configured PWM output occupying the step/dir 5 spot, this means that nothing funny has to be done to any spindle config, and any spindle gcode (M3) is unaffected.  Raster laser (M67, Analog Out) will use the dedicated PWM output solely.

Enjoy!
