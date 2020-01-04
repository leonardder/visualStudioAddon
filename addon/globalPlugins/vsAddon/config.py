# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter, https://github.com/leonardder/visualStudioAddon

import addonHandler
import config
import gui
import wx


# A config spec for visual studio settings within NVDA's configuration
confspec = {
}


class VSSettingsPanel(gui.SettingsPanel):
	"""a gui panel for NVDA settings dialog"""

	# Translators: title of a panel.
	title = _("Visual Studio")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

	def onSave(self):
		...

	@staticmethod
	def initConfigSection():
		# Add a seqtion to nvda's configuration for VS
		config.conf.spec["visualStudio"] = confspec
