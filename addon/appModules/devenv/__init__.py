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
import gui
from . import overlays
from . import config
from nvdaBuiltin.appModules import devenv as devenv_builtIn

# Initialize the translation system
addonHandler.initTranslation()


class AppModule(devenv_builtIn.AppModule):

	selectedIntellisenseItem: UIA = None
	openedIntellisensePopup = False
	readIntellisenseHelp: bool = False
	readIntellisenseItem: bool = False
	signatureHelpPlayed = False
	lastFocusedEditor: UIA.WpfTextView = None

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		super().chooseNVDAObjectOverlayClasses(obj, clsList)
		if isinstance(obj, UIA.UIA):

			if (
				obj.role == controlTypes.ROLE_TABCONTROL
				and obj.UIAElement.cachedClassName == "DocumentGroup"
			):
				clsList.insert(0, overlays.DocumentGroup)
			elif (
				obj.role == controlTypes.ROLE_TABCONTROL
				and obj.UIAElement.cachedClassName == "ToolWindowTabGroup"
			):
				clsList.insert(0, overlays.ToolTabGroup)
			elif (
				obj.role == controlTypes.ROLE_TAB
				and obj.parent
				and isinstance(obj.parent, overlays.DocumentGroup)
			):
				clsList.insert(0, overlays.DocumentTab)
			elif (
				obj.role == controlTypes.ROLE_TAB
				and obj.parent
				and isinstance(obj.parent, overlays.ToolTabGroup)
			):
				clsList.insert(0, overlays.ToolTab)

			if (
				obj.role == controlTypes.ROLE_UNKNOWN
				and obj.UIAElement.CachedClassName == "WpfSignatureHelp"
			):
				clsList.insert(0, overlays.ParameterInfo)

			if (
				obj.role == controlTypes.ROLE_TOOLTIP
				and (
					obj.UIAElement.cachedAutomationId == "completion tooltip"
					or (
						isinstance(obj.parent.next, UIA.UIA)
						and obj.parent.next.UIAElement.cachedAutomationId == "DefaultCompletionPresenter"
					)
				)
			):
				clsList.insert(0, overlays.DocumentationToolTip)

			if (
				obj.role == controlTypes.ROLE_EDITABLETEXT
				and obj.UIAElement.cachedClassName == "WpfTextView"
			):
				if (
					(
						obj.parent
						and obj.parent.parent
						and obj.parent.parent.parent
						and obj.parent.parent.parent.parent
						and isinstance(obj.parent.parent.parent.parent, overlays.DocumentTab)
					) or (
						obj.parent
						and obj.parent.parent
						and obj.parent.parent.parent
						and obj.parent.parent.parent.windowClassName == "GenericPane"
					)
				):
					clsList.insert(0, overlays.CodeEditor)
				elif (
					obj.parent
					and obj.parent.parent
					and obj.parent.parent.parent
					and obj.parent.parent
					and isinstance(obj.parent.parent.parent, UIA.UIA)
					and obj.parent.parent.parent.UIAElement.cachedAutomationId in (
						"ST:0:0:{34e76e81-ee4a-11d0-ae2e-00a0c90fffc3}",
					)
				):
					clsList.insert(0, overlays.OutputEditor)
				else:
					clsList.insert(0, overlays.TextEditor)

			if (
				obj.role == controlTypes.ROLE_TABLE
				and obj.parent
				and obj.parent.parent
				and obj.parent.parent.parent
				and isinstance(obj.parent.parent.parent, UIA.UIA)
				and obj.parent.parent.parent.UIAElement.cachedAutomationId in (
					"ST:0:0:{d78612c7-9962-4b83-95d9-268046dad23a}",
				)
			):
				clsList.insert(0, overlays.ErrorsListView)

			if (
				obj.UIAElement.cachedClassName in (
					"IntellisenseMenuItem",
				)
			):
				clsList.insert(0, overlays.IntellisenseMenuItem)

			if (
				obj.role == controlTypes.ROLE_STATICTEXT
				and obj.UIAElement.cachedClassName == "LiveTextBlock"
				and obj.previous
				and obj.previous.previous
				and isinstance(obj.previous.previous, UIA.UIA)
				and obj.previous.previous.UIAElement.cachedAutomationId in (
					"CompletionList",
					"listBoxCompletions",
				)
			):
				clsList.insert(0, overlays.IntellisenseLabel)

	def event_liveRegionChange(self, obj, nextHandler):
		name = obj.name

		if (
			isinstance(obj, overlays.IntellisenseLabel)
			or not obj.name
		):
			nextHandler()

		if isinstance(obj, overlays.IntellisenseLabel):
			# We should omit speaking of intellisense label
			return

		ui.message(name, speechPriority=speech.Spri.NOW)

	def event_gainFocus(self, obj, nextHandler):
		if (
			not isinstance(obj, overlays.TextEditor)
			or obj != self.lastFocusedEditor
		):
			self.lastFocusedEditor = obj
			nextHandler()
		else:
			pass
