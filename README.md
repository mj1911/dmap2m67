# IMG2M67

> ⚠️ **Under active development.** IMG2M67 is a work in progress — expect rough edges, breaking changes, and incomplete features.

A modern, Python3/PyQt6 GUI front-end to convert an image to M67 Analog Output GCODE for PWM laser raster on LinuxCNC/Mesa hardware.

> Copyright (C) 2026  rdtsc/mj1911 and raggielyle.  Permission is granted to study and create derivative works.  However, forking, changing a few lines, and attempting to call this yours is prohibited.  If you just wish to add/fix/improve something, please send a pull request or PM.  For PMs or general comments, try the LinuxCNC forums, IRC Libera #LinuxCNC, or Discord.

## Table of Contents

- [Overview](#overview)
- [Safety and Liability Disclaimer](#%EF%B8%8F-safety-and-liability-disclaimer)
- [Features](#features)
- [What's Working and What is Not](#whats-working-and-what-is-not)
- [Integrating M67 to LinuxCNC](#integrating-m67-to-linuxcnc)
- [License](#license)

## Overview

**IMG2M67** converts an image file into rasterized sequences of `M67 E0 Qnnn` followed by `G1` move commands.

## ⚠️ Safety and Liability Disclaimer

**READ THIS CAREFULLY BEFORE USING THIS SOFTWARE**

This software is provided for using a laser with a CNC machine.  This is potentially dangerous equipment. By using this software, you acknowledge and agree to the following:

### No Warranty

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. THE SOFTWARE MAY CONTAIN BUGS, ERRORS, OR DEFECTS THAT COULD CAUSE EQUIPMENT MALFUNCTION, PROPERTY DAMAGE, PERSONAL INJURY, EVEN DEATH.

### No Liability

IN NO EVENT SHALL THE AUTHORS, COPYRIGHT HOLDERS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE, INCLUDING BUT NOT LIMITED TO:

- Personal injury or loss of life
- Property damage or equipment damage
- Loss of data or work product
- Loss of business or profits
- Any direct, indirect, incidental, special, exemplary, or consequential damages

### User Responsibility

YOU ARE SOLELY RESPONSIBLE FOR:

1. **Safety Measures**: Implementing appropriate safety systems, emergency stops, interlocks, guards, and protective equipment according to applicable safety standards
2. **Testing and Validation**: Thoroughly testing this software in a safe environment before use on production equipment
3. **Supervision**: Never leaving CNC equipment running unattended
4. **Compliance**: Ensuring compliance with all applicable local, state, national, and international laws, regulations, and safety standards
5. **Professional Review**: Having this software reviewed by qualified engineers or safety professionals before use in any critical application
6. **Risk Assessment**: Understanding the risks involved in operating CNC machinery and taking appropriate precautions
7. **Maintenance**: Keeping all equipment properly maintained and in safe operating condition

### CNC-Specific Warnings

CNC machines are inherently dangerous. They can:

- Move rapidly and with great force
- Cause severe crushing injuries
- Generate projectiles from broken tools or workpieces
- Create fire and eye hazards from laser operation
- Produce dangerous smoke particulates
- Pose electrical hazards

**Do not operate CNC equipment unless you are trained and qualified to do so.**

### No Support Guarantee

The authors provide this software on a voluntary basis and are under no obligation to provide support, updates, bug fixes, or any assistance whatsoever.

### Assumption of Risk

BY USING THIS SOFTWARE, YOU EXPRESSLY ACKNOWLEDGE AND ASSUME ALL RISKS ASSOCIATED WITH ITS USE. If you do not agree to these terms, do not use this software.

---

## Features

### Settings Save/Load

The options and values chosen while using this app are saved between runs.

### PIL Image Open (Python-Image-Library)

The PIL importer supports almost all image formats *except* .svg sadly.

### Metric/Imperial Conversion

The user may select mm or inches, which is reflected in the target size.  This is also the units generated in the output GCODE, so set this to what your machine uses.

### Output Scaling via Target DPI/DPmm or Width

To set the output size, set either the width or the DPI/DPmm.  Aspect ratio is automatically maintained.  *The current implementation does not interpolate to a higher resolution, so the distance between moves will increase as the size is increased.*  Currently, to get more resolution at a larger size, a larger source image is needed.

### Touch Checkbox

Enabling the Touch checkbox pops up a touchpad entry for values.  This is friendly for touchscreens, as a mouse is not required.

### Vertical Checkbox

Enabling Vertical Passes creates a second, vertical output pass.  This effectively doubles the amount of power put into the work, and could result in a finer, artistic result.

### Save As

The Save As dialog will save the output GCODE to whatever filename entered.  Note that nothing is saved until the conversion is run.

### Conversion

The Conversion button checks all of the inputs for sane values, then generates the output GCODE.  Currently this outputs one `M67` and one `G1` instruction for every pixel in the image.  Depending on the source image, many of these could be identical, which results in redundant instructions.  When optimization gets added, these will be reduced, resulting in a smaller file.  

### Installation

img2M67 uses PyQt6 for the GUI.  The following dependencies must be installed prior:

1. PyQt6: Python bindings for the Qt6 toolkit.  Install this using your usual OS-install command, such as:

- Debian: `sudo apt install python3-pyqt6 libxcb-cursor0`
- Arch: `pamac install python-pyqt6`
- MacOS: `brew install pyqt6` etc.  Note I do not have a Mac to test.

2. Python Image Library (pillow):

- Debian: `sudo apt install python3-pil`
- Arch: `pamac install python-pillow`
- MacOS: `brew install python3-pil` etc.

With those installed, this app should run.  It may give some error about 'dbus UnknownMethod' on some Linuxes, which means a missing `xdg-desktop-portal-*` package.  This is currently a rabbit-hole being avoided, as we do not need DBUS for this app.  Some versions of Python / PIL libary may also complain about `getdata()`, saying it is depreciated in favor of `get_flattened_data()`.  These can be ignored for now.

Once running, the GUI first looks for saved settings.  If none, it creates defaults.  These settings are saved at close and loaded at start, so it "remembers" the last-used settings, including the last-opened image.

The GUI is just one screen, with controls on the left, and images on the right.  There is a minimum size of 1000x750 pixels (so will fit on a 1024x768 display), but it can be maximized to increase the size of the images (work-in-progress.)

The controls on the left allow you to select an image, adjust the conversion parameters, select an output gcode file, and perform the conversion.  

The images on the right include the original source image, the intermediate luma-converted-image, and a proposed rendering of the actual GCODE output, which is not working yet.  Luma ended up being a can-of-worms, as PIL luma mode is limited to 8 bits per pixel (range 0-255) but ideally we would want a much larger range than this.  A rework was attempted but reverted for now. It is hoped that armed with this tool, fewer failed jobs will result.

## What's Working and What is Not

### Working

- Settings save/load
- Image open, original image display
- "Intermediate" image display
- Metric/imperial conversion
- Sizing the output raster (not interpolated)
- checkbox for Touch
- Checkbox for Vertical Passes
- Conversion.  Not optimized yet.

### Not Working Yet

- GCODE preview.  This will come in a later version.
- Window resizing.  Currently not working.
- Image bit-depth.  PIL limits a luminance-only (greyscale) image to 8 bits, which equates to 255 levels.  We desire more than this, so work-arounds are being considered.
- GCODE optimization.  The output gcode can be optimized to produce a smaller file.

### Possible Additions

- Image RGB levels, brightness, contrast, invert, etc.
- Zoom on images

## Integrating M67 to LinuxCNC

- Mesa Anything-IO cards which support a PWM output might require a different firmware to be loaded to do "real" PWM.  A card like the 7c80 has a spindle "pot" output, which is really a PWM output + RC filter + opamp.  Spindle outputs are far too slow for laser raster; a dedicated PWM output is required.  The 7c80 card has a "7c801p_5abobd.bit" firmware available, which changes step/dir channel 5 into a dedicated PWM output.  Such firmware needs loaded using the mesaflash utility.  The exact details vary on which card is being used.
- Once physical PWM output is enabled, Mesa PWM outputs have higher resolution (14 bits? 0-8191) at lower frequences, and 12 bits (0-2047) up to 48kHz.  But to use a lower frequency, the travel speed must be reduced, so higher frequency is desirable.  Note that PWM dithering can produce ~16-bit output, but introduces some jitter which may be undesirable.
- Another consideration is that using more digits in the gcode makes the gcode file significantly larger, so fewer digits are desirable.  Therefore a compromise is using three digits for power, 0-999, which gives 1k intensity levels while still allowing 48kHz operation.  This is 3.92 times more resolution than the 255 levels afforded by hobby-grade lasers (assuming your laser can interpret the extra PWM detail and this software can generate them.)
- To make the link in HAL between Analog-out and the PWM, do something like `net  laserout  motion.analog-out-01  ->  hm2_7c80.0.pwmgen.01.value`.  Note that on the 7c80 card, PWM 0 is the spindle, and PWM 1 is the dedicated PWM output on step/dir 5.  This may be vastly different on other cards.
- To make the PWM output max-out at the chosen max power value such as 999, do `setp  hm2_7c80.0.pwmgen.01.scale  999`.  To set the PWM frequency (globally) to 48kHz, do `setp  hm2_7c80.0.pwmgen.pwm_frequency  48000`.  To enable the PWM, do `setp  hm2_7c80.0.pwmgen.00.enable = true`.  May want to tie that to a GUI button or some other safety measure, to enable/disable the laser.
- Note that since the 7c80 card has a configured PWM output occupying the step/dir 5 spot, this means that nothing funny has to be done to any spindle config - any spindle gcode (M3) is unaffected.  Raster laser (M67, Analog Out) will use the dedicated PWM output solely.

## License

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0).
See the [LICENSE](LICENSE) file for the full text.

This app uses work from raggielyle, whom was kind enough to allow use of his conversion code and also helped test this version of it.  It is our hope that such a GUI can be used for more LinuxCNC tools in the future.

This project uses subroutines from [ProbeBasic](https://github.com/kcjengr/probe_basic)
(Chris P / kcjengr) and [tool_length_probe](https://github.com/TooTall18T/tool_length_probe)
(TooTall18T), both...

**THIS SOFTWARE IS PROVIDED WITHOUT WARRANTY OF ANY KIND. THIS SOFTWARE IS
INTENDED FOR USE WITH POTENTIALLY DANGEROUS EQUIPMENT. BY USING THIS SOFTWARE,
YOU ACCEPT ALL RISKS AND AGREE THAT THE AUTHORS BEAR NO RESPONSIBILITY FOR ANY
INJURIES, DEATHS, PROPERTY DAMAGE, OR OTHER LOSSES THAT MAY RESULT FROM ITS USE.**

Enjoy!
