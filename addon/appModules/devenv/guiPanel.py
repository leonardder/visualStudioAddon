# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter, https://github.com/leonardder/visualStudioAddon

import addonHandler
import config
import gui
import wx

class VSSettingsPanel(gui.SettingsPanel):
	"""a gui panel for NVDA settings dialog"""

	# Translators: title of a panel.
	title = _("Visual Studio")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.announceBreakpointCheckBox = sHelper.addItem(
			# Translators: label of a checkbox which toggles the announcement of breakpoints via speech
			wx.CheckBox(self, wx.ID_ANY, label=_("&Announce breakpoints via speech"))
		)
		self.announceBreakpointCheckBox.SetValue(config.conf["visualStudio"]["announceBreakpoints"])

		self.beepOnBreakpointCheckBox = sHelper.addItem(
			# Translators: label of a checkbox which toggles the beep on breakpoints option
			wx.CheckBox(self, wx.ID_ANY, label=_("&Beep on  breakpoints"))
		)
		self.beepOnBreakpointCheckBox.SetValue(config.conf["visualStudio"]["beepOnBreakpoints"])

		self.reportIntelliSensePosInfoCheckBox = sHelper.addItem(
			# Translators: label of a checkbox which toggles reporting of intelliSense menu item position info
			wx.CheckBox(self, wx.ID_ANY, label=_("&Report intelliSense menu item position information"))
		)
		self.reportIntelliSensePosInfoCheckBox.SetValue(config.conf["visualStudio"]["reportIntelliSensePosInfo"])

	def onSave(self):
		vsConfig = config.conf["visualStudio"]
		vsConfig["announceBreakpoints"] = self.announceBreakpointCheckBox.IsChecked()
		vsConfig["beepOnBreakpoints"] = self.beepOnBreakpointCheckBox.IsChecked()
		vsConfig["reportIntelliSensePosInfo"] = self.reportIntelliSensePosInfoCheckBox.IsChecked()
