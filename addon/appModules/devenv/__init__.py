# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter,
# and Francisco R. Del Roio (https://github.com/leonardder/visualStudioAddon)

import os
import addonHandler
import controlTypes
import ui
from NVDAObjects import UIA
from globalCommands import SCRCAT_FOCUS
import speech
import config
import gui
from .guiPanel import VSSettingsPanel
from . import overlays
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
	lastFocusedEditor: UIA.WpfTextView = None

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
		if isinstance(obj, UIA.UIA):
			if (
				obj.parent
				and obj.parent.parent
				and obj.parent.parent.parent
				and isinstance(obj.parent.parent.parent, UIA.UIA)
				and obj.parent.parent.parent.UIAElement.cachedAutomationId.startswith("ST:0:0:")
			):
				clsList.insert(0, overlays.ToolContent)

			elif (
				obj.parent
				and obj.parent.parent
				and obj.parent.parent.parent
				and isinstance(obj.parent.parent.parent, UIA.UIA)
				and obj.parent.parent.parent.UIAElement.cachedAutomationId.startswith("D:0:0:")
			):
				clsList.insert(0, overlays.DocumentContent)

			elif obj.UIAElement.cachedClassName == "DocumentGroup":
				clsList.insert(0, overlays.DocumentGroup)
			elif obj.UIAElement.cachedClassName == "ToolWindowTabGroup":
				clsList.insert(0, overlays.ToolTabGroup)
			elif (
				obj.parent
				and isinstance(obj.parent, overlays.DocumentGroup)
			):
				clsList.insert(0, overlays.DocumentTab)
			elif (
				obj.parent
				and isinstance(obj.parent, overlays.ToolTabGroup)
			):
				clsList.insert(0, overlays.ToolTab)

			if (
				obj.role == controlTypes.ROLE_UNKNOWN
				and obj.UIAElement.CachedClassName == "WpfSignatureHelp"
			):
				clsList.insert(0, overlays.ParameterInfo)

			if obj.UIAElement.cachedAutomationId == "completion tooltip":
				clsList.insert(0, overlays.DocumentationToolTip)

			if obj.UIAElement.cachedClassName == "WpfTextView":
				if overlays.DocumentContent in clsList:
					clsList.insert(0, overlays.CodeEditor)
				else:
					clsList.insert(0, overlays.TextEditor)

			if obj.UIAElement.cachedClassName in (
				"IntellisenseMenuItem",
			):
				clsList.insert(0, overlays.IntellisenseMenuItem)

			if (
				obj.UIAElement.cachedClassName == "LiveTextBlock"
				and obj.previous
				and obj.previous.previous
				and isinstance(obj.previous.previous, UIA.UIA)
				and obj.previous.previous.UIAElement.cachedAutomationId == "CompletionList"
			):
				clsList.insert(0, overlays.IntellisenseLabel)

	def event_liveRegionChange(self, obj, nextHandler):
		name = obj.name

		if not obj.name:
			nextHandler()

		if isinstance(obj, overlays.IntellisenseLabel):
			return

		ui.message(name, speechPriority=speech.priorities.Spri.NOW)

	def event_gainFocus(self, obj, nextHandler):
		if (
			not isinstance(obj, overlays.TextEditor)
			or obj != self.lastFocusedEditor
		):
			self.lastFocusedEditor = obj
			nextHandler()
		else:
			pass
