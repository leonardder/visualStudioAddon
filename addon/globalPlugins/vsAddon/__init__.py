# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter,
# and Francisco R. Del Roio (https://github.com/leonardder/visualStudioAddon)

import gui
import globalPluginHandler
from logHandler import log
import sys

from appModules.devenv.config import VSSettingsPanel


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self):
		super().__init__()
		# add visual studio settings panel to the NVDA settings
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(VSSettingsPanel)
		VSSettingsPanel.initConfigSection()

	def terminate(self):
		super().terminate()
		settingsPanels = gui.settingsDialogs.NVDASettingsDialog.categoryClasses
		if VSSettingsPanel in settingsPanels:
			settingsPanels.remove(VSSettingsPanel)
