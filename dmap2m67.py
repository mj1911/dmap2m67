#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

''' App to convert image to M67 gcode (Analog Output) for laser raster, using
    modern Mesa hardware PWM.  Not for spindles or lasers connected as spindles!

    image2m67 - Image to M67 G-Code Converter
    Supported image types: pretty much everything except no .svg sadly.
    Usage notes and updates: https://github.com/mj1911/dmap2m67

    Copyright (C) <2026-?>  <mj1911/rdtsc and raggielyle1>
    This app is based on work by:
      raggielyle1           2026 Bruce Lyle   raggielyle1(A)gmail.com
      (https://forum.linuxcnc.org/plasma-laser/
       35064-new-laser-build-raster-engraving#342700)

    Version 0.01  20260408 - Initial code; conversion routine by Bruce.
      * Start basic design around PyQt5; quickly rework for PyQt6.
      * Design import section to alert missing dependencies (pyqt6, pillow.)
      * Implement QSettings to load and save options between runs.
      * Change default font to 12pt for better readability on touch screens.
      * Create touch UI dialog for data entry on touchscreens.
      * Got converter working, but limited to 256 gray levels due to Pillow's 
        convert('L') method.  TODO: Need to do RGB to Luminance conversion 
        ourselves to get more than 8 bits of resolution.
      * TODO: if any M67's are sequentially identical (redundant), omit them!
        Can likely optimize-out irrelevant moves too, reducing output file size.
      * Add image loading, display, and settings validation.
      * TODO: img_out is a graphicsView to preview the generated GCODE
      * Get inch and mm units working, including switching between them.
      * Auto-loads the last image at start if still valid.
      * Enabled sane limits for most controls.
      * Increased to three decimal places for inch units, two for mm.  Now can
        set target width, and height automatically scales.
      * Tried changing control colors; way too messy, reverted.
      * Changed all DP's to float, with 2/3 digits for in/mm.
'''

import sys
import os

# ensure only python3 is attempted...
VERSION = sys.version_info[0]
if VERSION != 3:
    print("Python version 3.xx required!  Get from: https://www.python.org/downloads/")
    exit()

# try to import dependencies
try:    # https://pypi.org/project/pyqt6/
    from PyQt6 import uic, QtGui, QtCore
    from PyQt6.QtWidgets import QMainWindow, QFileDialog, QDialog, QApplication, QLineEdit
    from PyQt6.QtCore import QPoint, QSettings, QSize
    from PyQt6.QtGui import QFont, QPixmap
except ImportError or ModuleNotFoundError:
    print("\nPyQt6 bindings missing!  Please install:")
    print("  Debian:  sudo apt install python3-pyqt6 libxcb-cursor0")
    print("  Arch:    pamac install python-pyqt6")
    print("  Mac:     brew install pyqt6")
    print("  Windows: pip install pyqt6")
    exit()

try:    # https://pypi.org/project/pillow/
    from PIL import Image, ImageQt
except ImportError or ModuleNotFoundError:
    print("\nPython Image Library (pillow) missing!  Please install:")
    print("  Debian:  sudo apt install python3-pil")
    print("  Arch:    pamac install python-pillow")
    print("  Mac:     brew install python3-pil")
    print("  Windows: pip install pillow")
    exit()


class dmap2m67GUI(QMainWindow):
    def __init__(self):
        super(dmap2m67GUI, self).__init__() # define self as an app
        self.main = uic.loadUi("dmap2m67.ui", self)  # load GUI
        self.load_settings()    # restore settings
        self.show()     # show main window quickly
        # setup links from control interaction to code
        self.pb_open.clicked.connect(self.open)
        self.rb_mm.clicked.connect(self.rb_mm_changed)
        self.rb_in.clicked.connect(self.rb_in_changed)
        # may be able to use self.validate as most of these callbacks
        self.le_image_dp.editingFinished.connect(self.validate)
        self.le_target_width.editingFinished.connect(self.target_width)
        self.le_target_dp.editingFinished.connect(self.target_dp)
        self.le_feedrate.editingFinished.connect(self.feed_rate)
        self.le_safe_z.editingFinished.connect(self.safe_z)
        self.le_work_z.editingFinished.connect(self.work_z)
        self.le_power_min.editingFinished.connect(self.power_min)
        self.le_power_max.editingFinished.connect(self.power_max)
        self.pb_saveas.clicked.connect(self.saveas)
        self.pb_convert.clicked.connect(self.convert)
        for le in self.findChildren(QLineEdit):
            if le.objectName().startswith("le_"):
                le.mousePressEvent = lambda event, line_edit=le: self.le_mousePressEvent(line_edit, event)

    def load_settings(self):    
        # Linux: ~/.config/RDTSC/dmap2m67.conf
        # Windows: HKCU\Software\RDTSC\dmap2m67
        self.settings = QSettings('RDTSC', 'dmap2m67')
        if not self.settings.contains('window_size'):   # if none, default
            self.settings.setValue('window_size', QSize(1000, 745))
            self.settings.setValue('window_position', QPoint(0, 0))
            self.settings.setValue('file_in', 'FileIn.png')
            self.settings.setValue('units', 'in')
            self.settings.setValue('image_dp', '72.0') # must set these as text
            self.settings.setValue('target_dp', '72.0')
            self.settings.setValue('target_width', '2.25') # others are calculated
            self.settings.setValue('feed_rate', '50')
            self.settings.setValue('safe_z', '-5.0')
            self.settings.setValue('work_z', '-8.0')
            self.settings.setValue('min_power', '0')
            self.settings.setValue('max_power', '999')
            self.settings.setValue('vertical', False)
            self.settings.setValue('touch', False)
            self.settings.setValue('file_out', 'FileOut.ngc')
            # get window metrics for one-time centering...
            qtRectangle = self.frameGeometry()
            centerPoint = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
            qtRectangle.moveCenter(centerPoint)
            self.move(qtRectangle.topLeft())
            # center this window in display
            centerPoint = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
            qtRectangle.moveCenter(centerPoint)
            self.move(qtRectangle.topLeft())
        # else restore previous values to UI
        self.resize(self.settings.value('window_size'))
        self.move(self.settings.value('window_position'))
        # and begin restoring all of the settings
        self.full_file_in = self.settings.value('file_in')
        self.speedload = True   # do try to load the last file immediately
        head, tail = os.path.split(self.full_file_in)
        self.lb_file_in.setText(tail)   # update display
        if 'in' == self.settings.value('units'): 
            self.rb_in.setChecked(True)
            self.rb_mm.setChecked(False)
            self.m = 1.0
        else: 
            self.rb_in.setChecked(False)
            self.rb_mm.setChecked(True)
            self.m = 25.4
        self.le_image_dp.setText(self.settings.value('image_dp'))
        self.le_target_width.setText(self.settings.value('target_width'))
        self.old_le_target_width = self.settings.value('target_width') # for tracking changes
        self.le_target_dp.setText(self.settings.value('target_dp'))
        self.le_feedrate.setText(self.settings.value('feed_rate'))
        self.le_safe_z.setText(self.settings.value('safe_z'))
        self.le_work_z.setText(self.settings.value('work_z'))
        self.le_power_min.setText(self.settings.value('min_power'))
        self.le_power_max.setText(self.settings.value('max_power'))
        if 'true' == self.settings.value('vertical'):
            self.cb_vertical.setChecked(True)
        if 'true' == self.settings.value('touch'):
            self.cb_touch.setChecked(True)
        self.full_file_out = self.settings.value('file_out')
        head, tail = os.path.split(self.full_file_out)
        self.lb_file_out.setText(tail)
        # now validate all these settings and update rest of display
        self.validate()
    
    def save_settings(self):
        self.settings.setValue('window_size', self.size())
        self.settings.setValue('window_position', self.pos())
        self.settings.setValue('file_in', self.full_file_in)
        if self.rb_in.isChecked(): 
            units='in'
        else: 
            units='mm'
        self.settings.setValue('units', units)
        self.settings.setValue('image_dp', self.le_image_dp.text())
        self.settings.setValue('target_dp', self.le_target_dp.text())
        self.settings.setValue('target_width', self.le_target_width.text())
        self.settings.setValue('feed_rate', self.le_feedrate.text())
        self.settings.setValue('safe_z', self.le_safe_z.text())
        self.settings.setValue('work_z', self.le_work_z.text())
        self.settings.setValue('min_power', self.le_power_min.text())
        self.settings.setValue('max_power', self.le_power_max.text())
        self.settings.setValue('vertical', self.cb_vertical.isChecked())
        self.settings.setValue('touch', self.cb_touch.isChecked())
        self.settings.setValue('file_out', self.full_file_out)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def open(self):
        fileName = self.full_file_in if self.full_file_in else os.getcwd()
        head, tail = os.path.split(fileName)
        if not self.speedload:  # for every subsequent open
            #print(f"head: {head}, tail: {tail}")
            dialog = QFileDialog(self)
            dialog.setWindowTitle("Open Image")
            dialog.setDirectory(head)
            dialog.setNameFilter("Image Files (*.*)")  # too many to list all
            dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            dialog.resize(800, 600)
            font = QFont()
            font.setPointSize(12)
            dialog.setFont(font)
            dialog.exec()
            fileName = (dialog.selectedFiles()[0] if dialog.selectedFiles()[0] else "")
            #print(f'returned fileName: {fileName}')
            head, tail = os.path.split(fileName)
            #print(f'fileName head: {head}, tail: {tail}')
        # TODO: validate that file is valid type...
        self.statusBar.showMessage("Opening image file...", 2000)
        try:
            self.img = Image.open(fileName)
            if self.img.mode != 'L':     # convert to grayscale if not already
                self.img_l = self.img.convert('L', colors=999)  # to match le_power_max
# NOTE THIS DOES NOT WORK!  Pillow's convert('L') only gives 256 levels of gray, 
# which is well below what LinuxCNC and Mesa hardware are capable of.
# We need to do the RGB to Luminance conversion ourselves to get more than 8 
# bits of resolution.  While here, we should be able to adjust other aspects of 
# the image also, such as contrast, brightness, and gamma, to get the best 
# results for laser...
                # self.img is the original image
                # self.img_l is the grayscale version used for processing
            print(f'Successfully opened image file: {tail}')
            self.statusBar.showMessage(f"Successfully opened image file: {tail}", 2000)
        except Exception as e:
            print(f"Error opening file!: {e}")
            self.statusBar.showMessage("Error opening file!", 2000)
            return
        # now show file name in UI since it opened successfully
        self.lb_file_in.setText(tail)
        # and set the self.full_file_in for later use
        self.full_file_in = fileName
        # display the source image, retaining aspect ratio
        pixmap = QPixmap(str(fileName))
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.img_src.size(), 
                            aspectRatioMode = QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.img_src.setPixmap(scaled_pixmap)
        # display intermediate image
        imgtmp = ImageQt.ImageQt(self.img_l)
        pixmap_l = QPixmap.fromImage(imgtmp)
        if not pixmap_l.isNull():
            scaled_pixmap_l = pixmap_l.scaled(self.img_luma.size(), 
                            aspectRatioMode = QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.img_luma.setPixmap(scaled_pixmap_l)
        # finally, a hack - click the selected units radio button to trigger
        # validation and update the display.
        if self.rb_mm.isChecked():
            self.rb_mm.click()
        else:
            self.rb_in.click()

    def le_mousePressEvent(self, line_edit, event):
        """Handle mouse press on line edits; if touch enabled, open touch dialog"""
        if not self.cb_touch.isChecked():
            return type(line_edit).mousePressEvent(line_edit, event)
        title = line_edit.objectName().replace("le_", "").replace("_", " ").title()
        self.touch_dialog(line_edit, title)

    def touch_dialog(self, field, title):
        """Open touch UI dialog for a touched line edit"""
        dialog = QDialog(self)
        uic.loadUi("dmap2m67-touch.ui", dialog)
        dialog.setWindowTitle(title)

        le_value = dialog.findChild(type(self.le_image_dp), "le_value")
        if le_value is None:
            return
        le_value.setText(field.text())

        for digit in range(10):
            button = dialog.findChild(type(self.pb_open), f"pb_{digit}")
            if button:
                button.clicked.connect(lambda checked, d=digit: self.touch_digit(le_value, str(d)))

        pb_dot = dialog.findChild(type(self.pb_open), "pb_dot")
        if pb_dot:
            pb_dot.clicked.connect(lambda: self.touch_digit(le_value, "."))

        pb_plus_minus = dialog.findChild(type(self.pb_open), "pb_plus_minus")
        if pb_plus_minus:
            pb_plus_minus.clicked.connect(lambda: self.touch_toggle_sign(le_value))

        pb_backspace = dialog.findChild(type(self.pb_open), "pb_backspace")
        if pb_backspace:
            pb_backspace.clicked.connect(lambda: self.touch_backspace(le_value))

        pb_clear = dialog.findChild(type(self.pb_open), "pb_clear")
        if pb_clear:
            pb_clear.clicked.connect(lambda: le_value.setText("0"))

        pb_ok = dialog.findChild(type(self.pb_open), "pb_ok")
        if pb_ok:
            pb_ok.clicked.connect(dialog.accept)

        pb_quit = dialog.findChild(type(self.pb_open), "pb_quit")
        if pb_quit:
            pb_quit.clicked.connect(dialog.reject)

        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            try:
                field.setText(le_value.text())
            except Exception as e:
                print(f"Invalid le_value.text() input: {e}")
                pass
    
    def touch_digit(self, le_value, digit):
        """Handle digit button press in touch dialog"""
        current = le_value.text()
        if current == "0" and digit != ".":
            le_value.setText(digit)
        else:
            le_value.setText(current + digit)
    
    def touch_backspace(self, le_value):
        """Handle backspace in touch dialog"""
        current = le_value.text()
        if len(current) > 1:
            le_value.setText(current[:-1])
        else:
            le_value.setText("0")
    
    def touch_toggle_sign(self, le_value):
        """Toggle sign in touch dialog"""
        current = le_value.text()
        if current.startswith("-"):
            le_value.setText(current[1:])
        else:
            le_value.setText("-" + current)

    def rb_mm_changed(self):
        """ Handle change to mm units """
        #self.m = 25.4
        self.validate() # check inputs and update display
        
    def rb_in_changed(self):
        """ Handle change to inch units """
        #self.m = 1.0
        self.validate()

    def target_width(self):
        target_w_old = float(self.old_le_target_width) if self.old_le_target_width else 1.0
        target_w = float(self.le_target_width.text())
        if target_w == target_w_old:    # if no change
            return
        # recalculate size of target_h
        x,y = self.img_l.size   # image size in pixels
        image_w = float(self.lb_image_width.text())
        image_dp = float(self.le_image_dp.text())
        aspect_ratio = float(y / x) # ratio of y to x (less than 1)
        target_h = float(target_w * aspect_ratio)
        # recalculate target_dp
        targetdp = (target_w / image_w) * image_dp
        targetdp = (image_dp / targetdp) * image_dp
        if self.rb_in.isChecked():
            self.le_target_dp.setText(f'{targetdp:.2f}')
            self.le_target_width.setText(f"{target_w:.3f}")
            self.lb_target_height.setText(f"{target_h:.3f}")
        else:
            self.le_target_dp.setText(f'{targetdp:.3f}')
            self.le_target_width.setText(f"{target_w:.2f}")
            self.lb_target_height.setText(f"{target_h:.2f}")
        # update old value for tracking changes
        self.old_le_target_width = self.le_target_width.text() 

    def target_dp(self):
        self.validate()

    def feed_rate(self):
        self.validate()

    def safe_z(self):
        self.validate()

    def work_z(self):
        self.validate()

    def power_min(self):
        self.validate()

    def power_max(self):
        self.validate()

    def saveas(self):
        #print(f'full_file_out: {self.full_file_out}')
        lastfile = self.full_file_out if self.full_file_out else os.getcwd()
        #print(f'lastfile: {lastfile}')
        lastdir = os.path.dirname(lastfile) if os.path.isfile(lastfile) else lastfile
        #print(f'lastdir: {lastdir}')
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Save M67 GCODE")
        dialog.setDirectory(lastdir)
        dialog.setNameFilter("GCODE Files (*.ngc *.nc *.txt)")
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.resize(800, 600)
        font = QFont()
        font.setPointSize(12)
        dialog.setFont(font)
        dialog.exec()
        fileName = (dialog.selectedFiles()[0] if dialog.selectedFiles() else "")
        #print(f'returned filename: {fileName}')
        head, tail = os.path.split(fileName)
        #print(f'Head: {head}  Tail: {tail}')
        self.lb_file_out.setText(tail)
        # must set self.full_file_out for later use
        self.full_file_out = fileName

    def validate(self):
        """ Validate all inputs, update display, report issues """
        if self.speedload:  # attempt to load image initially
            self.open()   # this attempts to open the last file
            self.speedload = False
        # display image size in pixels
        img_w, img_h = self.img_l.size
        self.lb_image_px.setText(f"{img_w}x{img_h}")
        # handle mismatches between current and previous units
        if self.rb_mm.isChecked() and self.m != 25.4:   # need to convert in to mm
            tmp = float(self.le_image_dp.text()) / 25.4
            self.le_image_dp.setText(f"{tmp:.3f}")
            tmp = float(self.le_target_dp.text()) / 25.4
            self.le_target_dp.setText(f"{tmp:.3f}")
            tmp = float(self.le_target_width.text()) * 25.4
            self.le_target_width.setText(f"{tmp:.2f}")
            self.m = 25.4
        elif self.rb_in.isChecked() and self.m != 1.0:  # convert mm to in
            tmp = float(self.le_image_dp.text()) * 25.4
            self.le_image_dp.setText(f"{tmp:.2f}")
            tmp = float(self.le_target_dp.text()) * 25.4
            self.le_target_dp.setText(f"{tmp:.2f}")
            tmp = float(self.le_target_width.text()) / 25.4
            self.le_target_width.setText(f"{tmp:.3f}")
            self.m = 1.0
        elif self.rb_mm.isChecked() and self.m == 25.4: # mm but recalculate?
            pass
        elif self.rb_in.isChecked() and self.m == 1.0:  # in but recalculate?
            pass
        else:
            print("Error: Cannot determine inch/mm state!")
            self.statusBar.showMessage("Error: Cannot determine inch/mm state!", 2000)
            return False
        # validate image size
        x,y = self.img_l.size
        if x <= 1 or y <= 1:
            print("Error: Image has invalid dimensions!")
            self.statusBar.showMessage("Error: Image has invalid dimensions!", 2000)
            return False
        # check DPI
        imagedpnative = round(float(self.img_l.info.get('dpi', (72, 72))[0] / self.m))  # default to 72 DPI
        imagedp = float(self.le_image_dp.text())
        if imagedp > imagedpnative:
            print(f"Warning: Image native Dot-Pitch ({imagedpnative}) is less "
                  f"than selected image: ({imagedp}).  This loses detail.")
            self.statusBar.showMessage("Warning: native image Dot-Pitch is less than target DP!", 2000)
        if imagedp <= 0:
            print("Error: Image DP must be greater than 0!")
            self.le_image_dp.setText("1.0")
            self.statusBar.showMessage("Error: Image DP must be greater than 0!", 2000)
            return False
        targetdp = float(self.le_target_dp.text())
        if targetdp <= 0:
            print("Error: Target DP must be greater than 0!")
            self.le_target_dp.setText("1.0")
            self.statusBar.showMessage("Error: Target DP must be greater than 0!", 2000)
            return False
        # run through calculations to update display of image and target dimensions
        if self.rb_in.isChecked():
            img_width = float(x / imagedp)
            img_height = float(y / imagedp)
            self.lb_image_width.setText(f"{img_width:.3f}")
            self.lb_image_height.setText(f"{img_height:.3f}")
        else:
            img_width = float(x / imagedp)
            img_height = float(y / imagedp)
            self.lb_image_width.setText(f"{img_width:.2f}")
            self.lb_image_height.setText(f"{img_height:.2f}")
        # calculate target dimensions
        dpratio = float(imagedp / targetdp)
        target_w = float(img_width * dpratio)
        target_h = float(img_height * dpratio)
        if self.rb_in.isChecked():  # three decimals for inches, two for mm
            self.le_target_width.setText(f"{target_w:.3f}")
            self.lb_target_height.setText(f"{target_h:.3f}")
        else:
            self.le_target_width.setText(f"{target_w:.2f}")
            self.lb_target_height.setText(f"{target_h:.2f}")
        # check other inputs
        feedrate = int(self.le_feedrate.text())
        if feedrate <1 or feedrate > 5000:
            print("Error: Feed rate must be between 1 and 5000!")
            self.le_feedrate.setText("50")
            self.statusBar.showMessage("Error: Feed rate must be between 1 and 5000!", 2000)
        safez = float(self.le_safe_z.text())
        if safez < -100.0 or safez > 100.0:
            print("Error: Safe Z position must be between -100 and 100!")
            self.le_safe_z.setText("-5.0")
            self.statusBar.showMessage("Error: Safe Z position must be between -100 and 100!", 2000)
        workz = float(self.le_work_z.text())
        if workz < -100.0 or workz > 100.0:
            print("Error: Work Z position must be between -100 and 100!")
            self.le_work_z.setText("-8.0")
            self.statusBar.showMessage("Error: Work Z position must be between -100 and 100!", 2000)
        powermin = int(self.le_power_min.text())
        if powermin < 0 or powermin > 999:
            print("Error: Minimum power must be between 0 and 999!")
            self.le_power_min.setText("0")
            self.statusBar.showMessage("Error: Minimum power must be between 0 and 999!", 2000)
        powermax = int(self.le_power_max.text())
        if powermax < 0 or powermax > 999:
            print("Error: Maximum power must be between 0 and 999!")
            self.le_power_max.setText("999")
            self.statusBar.showMessage("Error: Maximum power must be between 0 and 999!", 2000)
        return True

    def convert(self):
        """ Convert the loaded image to M67 GCODE using the current settings """
        # validate settings...
        if not self.validate():
            print("Settings error! Please check your inputs.")
            self.statusBar.showMessage("Error in one or more settings!", 2000)
            return
# start of raggielye's code
        #if len(sys.argv) != 11:
        #  print("ERROR: Wrong number of arguments!")
        #  return 1
        
        # Parse arguments
        #input_file = sys.argv[1]
        #target_width_mm = float(sys.argv[2])
        #dpi = int(sys.argv[3])
        #feed_rate = int(sys.argv[4])
        #safe_z = float(sys.argv[5])
        #engrave_z = float(sys.argv[6])
        #min_power = int(sys.argv[7])
        #max_power = int(sys.argv[8])
        #cross_hatch = sys.argv[9]
        #output_file = sys.argv[10]
        input_file = self.full_file_in
# NOTE: need units conversion here!
        target_width_mm = float(self.le_target_width.text())
        #dpi = int(self.le_target_dp.text())
# NOTE: unsure if DPI being a float will work...
        dpi = float(self.le_target_dp.text())
        feed_rate = int(self.le_feedrate.text())
        safe_z = float(self.le_safe_z.text())
        engrave_z = float(self.le_work_z.text())
        min_power = int(self.le_power_min.text())
        max_power = int(self.le_power_max.text())
        vertical = 'y' if self.cb_vertical.isChecked() else 'n'
        output_file = self.full_file_out
        
        print(f"Converting: {os.path.basename(input_file)}")
        print(f"Power range: {min_power}-{max_power}")

        try:
          # Load image
          img = Image.open(input_file)
          # NOTE: eventually want to try process raw RGB data instead of L mode.
          if img.mode != 'L':
              img = img.convert('L')
          orig_w, orig_h = img.size
          
          # Calculate new size
          pixels_per_mm = dpi / 25.4
          target_px_w = int(target_width_mm * pixels_per_mm)
          aspect_ratio = orig_h / orig_w
          target_px_h = int(target_px_w * aspect_ratio)
            
          actual_mm_w = target_px_w / pixels_per_mm
          actual_mm_h = target_px_h / pixels_per_mm
          mm_per_pixel = 25.4 / dpi
            
          print(f"Image size: {target_px_w}x{target_px_h} pixels")
          print(f"Physical size: {actual_mm_w:.1f}x{actual_mm_h:.1f} mm")
          print(f"mm per pixel: {mm_per_pixel:.3f}")
        
          # Resize
          # TODO: are there different modes for resize?
          img = img.resize((target_px_w, target_px_h))
          if os.name == 'nt':   # windows does not have get_flattened_data()
            pixels = list(img.getdata())
#            r = list(img.getdata(0))
#            g = list(img.getdata(1))
#            b = list(img.getdata(2))
          else:                 # linux depreciated getdata() before, now?
            pixels = list(img.getdata())
#            r = list(img.getdata(0))
#            g = list(img.getdata(1))
#            b = list(img.getdata(2))

          # Pre-multiply the transform coefficients by the power range
#          Rc = 0.299 * (max_power - min_power)
#          Gc = 0.587 * (max_power - min_power)
#          Bc = 0.114 * (max_power - min_power)

          # Generate G-code
          with open(output_file, 'w') as f:
            # Header
            f.write('; dmap2m67 - laser raster engraving by raggielyle and rdtsc\n')
            f.write(f'; Image: {os.path.basename(input_file)}\n')
            f.write(f'; Size: {actual_mm_w:.1f}x{actual_mm_h:.1f} mm\n')
            f.write(f'; DPI: {dpi}\n')
            f.write(f'; Feed: {feed_rate}\n')
            f.write(f'; Power: {min_power}-{max_power}\n\n')

            # Setup
            f.write('G21\nG90\nG64\nG17\nG54\n\n')
            
            # Initialize
            f.write(f'F{feed_rate}\n')
            f.write(f'G0 Z{safe_z:.1f}\n')
            f.write('G0 X0 Y0\n')
            f.write(f'G0 Z{engrave_z:.1f}\n')
            #f.write('M3\n\n')
            
            # HORIZONTAL PASSES
            f.write('\n; --- HORIZONTAL PASSES ---\n')
            print("\nGenerating horizontal passes...")
            
            for y in range(target_px_h):
              # Flip Y: image row y (0=top) -> machine Y (target_px_h-1-y)*mm_per_pixel
              y_pos = (target_px_h - 1 - y) * mm_per_pixel
            
              if y % 2 == 0:
                # Left to right
                f.write(f'M67 E1 Q0\nG0 X0 Y{y_pos:.3f}\n')
                for x in range(target_px_w):
                  pixel = pixels[y * target_px_w + x]
                  # TODO: L-mode limits the depth resolution to 256 levels!
# Q: How does Pillow calculate the Luminance value in L mode from an RGB image?
# A: Pillow uses a standard formula for converting RGB to Luminance (L): 
#    L = R * 0.299 + G * 0.587 + B * 0.114. 
# This formula weights the color channels based on human perception of brightness.
# So we need to do this on each RGB pixel so that we get more than 8 bits of resolution!
# Suppose we could pre-multiply these coefficients by the max_power to get a 
# direct mapping to M67 power level.  
# This has it's own set of hurdes, as now the RGB data must be split...
#R,G,B = img.split()
                  #R = r[y * target_px_w + x]
                  #G = g[y * target_px_w + x]
                  #B = b[y * target_px_w + x]
                  #power = min_power + int(R*Rc + G*Gc + B*Bc)
# This no-go... out of time to troubleshoot.  Reverting changes.
                  power = min_power + int((max_power - min_power) * (255 - pixel) / 255)
                  f.write(f'M67 E1 Q{power}\n')
                  #f.write(f'G1 X{x*mm_per_pixel:.3f} S{power}\n')
                  f.write(f'G1 X{x*mm_per_pixel:.3f}\n')
                    
                else:
                # Right to left
                  f.write(f'M67 E1 Q0\nG0 X{actual_mm_w:.3f} Y{y_pos:.3f}\n')
                  for x in range(target_px_w-1, -1, -1):
                    pixel = pixels[y * target_px_w + x]
                    #R = r[y * target_px_w + x]
                    #G = g[y * target_px_w + x]
                    #B = b[y * target_px_w + x]
                    #power = min_power + int(R*Rc + G*Gc + B*Bc)
# This no-go... out of time to troubleshoot.  Reverting changes.
                    power = min_power + int((max_power - min_power) * (255 - pixel) / 255)
                    f.write(f'M67 E1 Q{power}\n')
                    #f.write(f'G1 X{x*mm_per_pixel:.3f} S{power}\n')
                    f.write(f'G1 X{x*mm_per_pixel:.3f}\n')
            
                if y % 50 == 0:
                  print(f" Row {y+1}/{target_px_h}")
            
            # VERTICAL PASSES
            if vertical.lower() == 'y':
              f.write('\n; --- VERTICAL PASSES ---\n')
              print("\nGenerating vertical passes...")
              #print("DEBUG: This should engrave on the way UP, not on the way DOWN!")
            
              for x in range(target_px_w):
                x_pos = x * mm_per_pixel
                if x % 2 == 0:
                  # Even columns: bottom to top (engrave on the way UP)
                  f.write(f'M67 E1 Q0\nG0 X{x_pos:.3f} Y0\n')
                  # We want to go from Y=0 to Y=max
                  # Read pixels from BOTTOM (image row target_px_h-1) to TOP (image row 0)
                  for step in range(target_px_h):
                    # step: 0 to target_px_h-1 (bottom to top in machine coords)
                    # image_y: target_px_h-1 to 0 (bottom to top in image)
                    image_y = target_px_h - 1 - step
                    pixel = pixels[image_y * target_px_w + x]
                    # NOTE: L-mode limits the depth resolution to 256 levels!
                    power = min_power + int((max_power - min_power) * (255 - pixel) / 255)
                    current_y = step * mm_per_pixel # 0 to max
                    f.write(f'M67 E1 Q{power}\n')
                    f.write(f'G1 Y{current_y:.3f}\n')
                else:
                  # Odd columns: top to bottom (engrave on the way DOWN)
                  f.write(f'M67 E1 Q0\nG0 X{x_pos:.3f} Y{actual_mm_h:.3f}\n')
                  # We want to go from Y=max to Y=0
                  # Read pixels from TOP (image row 0) to BOTTOM (image row target_px_h-1)
                  for step in range(target_px_h):
                    # step: 0 to target_px_h-1 (represents position from top)
                    image_y = step # 0 to target_px_h-1 (top to bottom in image)
                    pixel = pixels[image_y * target_px_w + x]
                    # NOTE: L-mode limits the depth resolution to 256 levels!
                    power = min_power + int((max_power - min_power) * (255 - pixel) / 255)
                    current_y = actual_mm_h - (step * mm_per_pixel) # max to 0
                    f.write(f'M67 E1 Q{power}\n')
                    f.write(f'G1 Y{current_y:.3f}\n')
                if x % 50 == 0:
                    print(f" Column {x+1}/{target_px_w}")
            
            f.write('M67 E1 Q0\n')
            # End program
            f.write('\n; --- END ---\n')
            #f.write('M5\n')
            f.write(f'G0 Z{safe_z:.1f}\n')
            f.write('G0 X0 Y0\n')
            f.write('M2\n')
            
            print(f"\n✅ G-code written to: {output_file}")
            # TODO: would be nice to see the size of this file
            # TODO: remove ancillary moves (like G1 with no laser change) to reduce file size?
            # TODO: show optimized file size after removing redundant moves?
            # Show sample of vertical section (this doesn't seem to work for me)
            if vertical.lower() == 'y' and os.path.exists(output_file):
              with open(output_file, 'r') as f:
                lines = f.readlines()
                
                # Find vertical section
                for i, line in enumerate(lines):
                  if 'VERTICAL PASSES' in line:
                    print("\n=== SAMPLE OF VERTICAL SECTION ===")
                    # Show first 20 lines of vertical section
                    for j in range(i, min(i+20, len(lines))):
                      print(f" {lines[j].rstrip()}")
                      print("...")
                  break
        #    return 0

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        #    return 1
# end of raggielyle's code


def main():
    dmap2m64 = QApplication([])
    window = dmap2m67GUI()
    dmap2m64.exec()
    del window, dmap2m64

if __name__ == '__main__':
    main()

# EOF