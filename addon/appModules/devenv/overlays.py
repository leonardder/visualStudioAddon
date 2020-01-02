# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter,
# and Francisco R. Del Roio (https://github.com/leonardder/visualStudioAddon)

import comtypes
import scriptHandler
import speech
import ui
import api

from NVDAObjects.UIA import Toast_win8 as Toast
from NVDAObjects.UIA import UIA, WpfTextView
import controlTypes
from NVDAObjects.behaviors import EditableTextWithSuggestions


class TextEditor(WpfTextView):
	pass


class ParameterInfo (Toast):
	role = controlTypes.ROLE_TOOLTIP

	def _get_description(self):
		return ""


class IntellisenseMenuItem(UIA):

	def _get_editor(self):
		focus = api.getFocusObject()

		if isinstance(focus, CodeEditor):
			return focus

	def _isHighlighted(self):
		try:
			return "[HIGHLIGHTED]=True" in self.UIAElement.CurrentItemStatus
		except COMError:
			try:
				return "[HIGHLIGHTED]=True" in self.UIAElement.CachedItemStatus
			except COMError:
				return False

	def event_UIA_itemStatus(self):
		if self._isHighlighted():
			if self.appModule.selectedIntellisenseItem != self:
				if not self.appModule.readIntellisenseHelp:
					speech.cancelSpeech()
				ui.message(self.name)

				self.appModule.selectedIntellisenseItem = self
			if self.editor and not self.appModule.openedIntellisensePopup:
				self.editor.event_suggestionsOpened()
			if self.appModule.readIntellisenseHelp:
				self.appModule.readIntellisenseHelp = False

	def event_nameChange(self):
		if self._isHighlighted():
			self.event_UIA_itemStatus()

	event_UIA_elementSelected = event_UIA_itemStatus


class IntellisenseLabel(UIA):

	def event_liveRegionChange(self):
		if not self.appModule.openedIntellisensePopup:
			focus = api.getFocusObject()
			if isinstance(focus, CodeEditor):
				focus.event_suggestionsOpened()
			super().event_liveRegionChange()
			self.appModule.readIntellisenseHelp = True


class CodeEditor(EditableTextWithSuggestions, WpfTextView):
	"""
	The code editor overlay class.
	"""

	def _get_documentTab(self) -> UIA:
		currentObj = self

		while currentObj:
			currentObj = currentObj.parent
			if isinstance(currentObj, DocumentTab):
				break

		if currentObj:
			return currentObj

	def _get_name(self):
		return self.documentTab.name

	def _get_positionInfo(self):
		return self.documentTab.positionInfo

	def event_gainFocus(self):
		if self.appModule.openedIntellisensePopup:
			self.event_suggestionsClosed()
		else:
			super().event_gainFocus()

	def event_suggestionsClosed(self):
		if self.appModule.openedIntellisensePopup:
			self.appModule.openedIntellisensePopup = False
			self.appModule.selectedIntellisenseItem = None
			super().event_suggestionsClosed()

	def event_suggestionsOpened(self):
		if not self.appModule.openedIntellisensePopup:
			self.appModule.openedIntellisensePopup = True
			super().event_suggestionsOpened()

	def event_loseFocus(self):
		self.event_suggestionsClosed()

	@scriptHandler.script(
		gesture="kb:NVDA+d",
		# Translators: Help message for read documentation script
		description=_("Tries to read documentation.")
	)
	def script_readDocumentation(self, gesture):
		firstChild = api.getForegroundObject().firstChild
		documentationObject: UIA = None

		if (
			isinstance(firstChild, UIA)
			and firstChild.UIAElement.CachedClassName == "Popup"
		):
			popupChild = firstChild.firstChild

			if isinstance(popupChild, ParameterInfo):
				# This is the parameter info object
				documentationObject = popupChild

			elif (
				isinstance(popupChild, UIA)
				and popupChild.UIAElement.CachedClassName == "Popup"
				and isinstance(popupChild.firstChild, DocumentationToolTip)
			):
				# Documentation about keywords, classes, interfaces and
				# methods are inside a tooltip container.
				documentationObject = popupChild.firstChild

		if documentationObject:
			helpText: str = ""

			if isinstance(documentationObject, ParameterInfo):
				textInfo = documentationObject.firstChild.next.next.next.makeTextInfo(
					textInfos.POSITION_ALL
				)
				helpText = f"{textInfo.text}\n{documentationObject.firstChild.next.name}"

			elif isinstance(documentationObject, DocumentationToolTip):
				for child in documentationObject.children:
					helpText += f"{child.name}\n"

			if len(helpText) > 0:
				if scriptHandler.getLastScriptRepeatCount() > 0:
					ui.browseableMessage(helpText)
				else:
					ui.message(helpText)
		else:
			ui.message(
				# Translators: Announced when documentation cannot be found.
				_("Cannot find documentation.")
			)

