# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter,
# and Francisco R. Del Roio (https://github.com/leonardder/visualStudioAddon)

import addonHandler
import controlTypes
import ui
from NVDAObjects import UIA
from globalCommands import SCRCAT_FOCUS
import speech
import config
import gui
from .guiPanel import VSSettingsPanel
from nvdaBuiltin.appModules import devenv as devenv_builtIn
# Initialize the translation system
addonHandler.initTranslation()

# A config spec for visual studio settings within NVDA's configuration
confspec = {
}


class AppModule(devenv_builtIn.AppModule):

	selectedIntellisenseItem: UIA = None
	openedIntellisensePopup = False
	readIntellisenseHelp: bool = False
	signatureHelpPlayed = False

	def __init__(self, processID, appName=None):
		super().__init__(processID, appName)
		# add visual studio settings panel to the NVDA settings
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(VSSettingsPanel)
		# Add a seqtion to nvda's configuration for VS
		config.conf.spec["visualStudio"] = confspec

	def terminate(self):
		super().terminate()
		settingsPanels = gui.settingsDialogs.NVDASettingsDialog.categoryClasses
		if VSSettingsPanel in settingsPanels:
			settingsPanels.remove(VSSettingsPanel)

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if isinstance(obj, UIA):
			if (
				obj.UIAElement.CachedClassName == "WpfTextView"
				and obj.role == controlTypes.ROLE_EDITABLETEXT
			):
				from .overlays import TextEditor
				clsList.insert(0, TextEditor)
			elif (
				obj.role == controlTypes.ROLE_UNKNOWN
				and obj.UIAElement.CachedClassName == "WpfSignatureHelp"
			):
				from .overlays import ParameterInfo
				clsList.insert(0, ParameterInfo)

			elif obj.UIAElement.cachedClassName in (
				"IntellisenseMenuItem",
			):
				from .overlays import IntellisenseMenuItem
				clsList.insert(0, IntellisenseMenuItem)


	def event_liveRegionChange(self, obj, nextHandler):
		name = obj.name
		if not obj.name:
			nextHandler()
		ui.message(name, speechPriority=speech.priorities.Spri.NOW)

