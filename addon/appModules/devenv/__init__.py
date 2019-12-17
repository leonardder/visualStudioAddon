# appModule for visual studio
# author: mohammad suliman (mohmad.s93@gmail.com)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016 Mohammad Suliman

from comtypes import COMError

import addonHandler
from NVDAObjects.UIA import UIA, WpfTextView
from NVDAObjects.UIA import Toast_win8 as Toast
from NVDAObjects.behaviors import RowWithoutCellObjects, RowWithFakeNavigation
from NVDAObjects.IAccessible import IAccessible, ContentGenericClient
from NVDAObjects.window import Desktop
from NVDAObjects import NVDAObjectTextInfo
import textInfos
import controlTypes
import UIAHandler
import api
import ui
import tones
from logHandler import log
import eventHandler
import scriptHandler
from globalCommands import SCRCAT_FOCUS
import re
import speech
import config
import gui
import wx
from nvdaBuiltin.appModules import devenv as devenv_builtIn


def _(x):
	"""Return the value itself as passed. This is defined just to hide python warnings."""
	return x


# Initialize the translation system
addonHandler.initTranslation()

# A config spec for visual studio settings within NVDA's configuration
confspec = {
	"announceBreakpoints": "boolean(default=True)",
	"beepOnBreakpoints": "boolean(default=True)",
	"reportIntelliSensePosInfo": "boolean(default=False)"
}

# Global vars
# Whether last focused object was an intelliSense item
intelliSenseLastFocused = False
# Last focused intelliSense object
lastFocusedIntelliSenseItem = None
# Whether the caret has moved to a different line in the code editor
caretMovedToDifferentLine = False


class AppModule(devenv_builtIn.AppModule):

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
		"""
		Selects overlay implementation for objects.
		"""

		if isinstance(obj, UIA):
			if (
				obj.role == controlTypes.ROLE_TABCONTROL
				and obj.UIAElement.CachedClassName == "DocumentGroup"
			):
				clsList.insert(0, DocumentGroup)

			if (
				obj.role == controlTypes.ROLE_TAB
				and obj.UIAElement.CachedClassName == "TabItem"
				and isinstance(obj.parent, DocumentGroup)
			):
				clsList.insert(0, DocumentTab)

			if (
				obj.role == controlTypes.ROLE_MENUITEM
				and obj.UIAElement.CachedClassName == "IntellisenseMenuItem"
			):
				clsList.insert(0, IntelliSenseMenuItem)

			if (
				obj.UIAElement.CachedClassName == "MenuItem"
				and obj.role == controlTypes.ROLE_MENUITEM
			):
				clsList.insert(0, VSMenuItem)

			if (
				obj.UIAElement.CachedClassName == "TextMarker"
				and obj.role == controlTypes.ROLE_UNKNOWN
				# To avoid AttributeError exceptions
				and obj.name
				and obj.name.startswith("Breakpoint")
			):
				clsList.insert(0, Breakpoint)

			if (
				obj.UIAElement.CachedClassName == "WpfTextView"
				and obj.role == controlTypes.ROLE_EDITABLETEXT
			):
				clsList.insert(0, TextEditor)

			if (
				obj.role == controlTypes.ROLE_DATAITEM
				and obj.UIAElement.CachedClassName == "ListViewItem"
			):
				clsList.insert(0, ErrorsListItem)

			if (
				obj.role == controlTypes.ROLE_UNKNOWN
				and obj.UIAElement.CachedClassName == "WpfSignatureHelp"
			):
				clsList.insert(0, ParameterInfo)

			if (
				obj.UIAElement.CachedClassName == "ViewPresenter"
				and obj.role == controlTypes.ROLE_PANE
			):
				clsList.insert(0, EditorAncestor)

		if (
			obj.windowClassName == 'TREEGRID'
			and obj.role == controlTypes.ROLE_WINDOW
		):
			clsList.insert(0, VarsTreeView)

		if (
			obj.name is None
			and obj.windowClassName == "TREEGRID"
			and obj.role == controlTypes.ROLE_PANE
		):
			clsList.insert(0, BadVarView)

		if (
			obj.name == "Quick Info Tool Tip"
			and obj.role == controlTypes.ROLE_TOOLTIP
		):
			clsList.insert(0, QuickInfoToolTip)

		if (
			obj.role == controlTypes.ROLE_LISTITEM
			and obj.windowClassName == "TBToolboxPane"
		):
			clsList.insert(0, ToolboxItem)

		if (
			obj.name == "Active Files"
			and obj.role in (controlTypes.ROLE_DIALOG, controlTypes.ROLE_LIST)
		):
			clsList.insert(0, SwitcherDialog)

		if (
			isinstance(obj, IAccessible)
			and obj.windowClassName.startswith("WindowsForms10.")
			and obj.windowText != "PropertyGridView"
		):
			clsList.insert(0, FormsComponent)

	def event_NVDAObject_init(self, obj):
		if obj.name == "Active Files" and obj.role in (controlTypes.ROLE_DIALOG, controlTypes.ROLE_LIST):
			# This object reports the descktop object as its parent, this causes 2 issues
			# Redundant announcement of the foreground object
			# and losing the real foreground object which makes reporting the status bar script not reliable, which is
			# crusial for breakpoint reporting to work.
			obj.role = controlTypes.ROLE_LIST
			parent = obj.parent
			if isinstance(parent, Desktop):
				obj.parent = api.getForegroundObject()
			# Description here also is redundant, so, remove it
			obj.description = ""
		elif obj.windowClassName == "ToolWindowSelectAccList":
			# All objects with this window class name have a description which is identical to the name
			# don't think that someone is interested to hear it
			obj.description = ""

	def event_appModule_loseFocus(self):
		global intelliSenseLastFocused
		global lastFocusedIntelliSenseItem
		lastFocusedIntelliSenseItem = None
		intelliSenseLastFocused = False

	def event_gainFocus(self, obj, nextHandler):
		global intelliSenseLastFocused, lastFocusedIntelliSenseItem
		if (
			isinstance(obj, UIA)
			and obj.UIAElement.currentClassName == "WpfTextView"
			and obj.role == controlTypes.ROLE_EDITABLETEXT
		):
			# In many cases, the editor fire focus events when intelliSense menu is opened, which leads to a lengthy
			# announcements after reporting the current intelliSense item, so allow the focus to return to the editor
			# if that happens, but don't report the focus event, and set the navigator object to be last reported
			# intelliSense item to allow the user to review
			if self._isCompletionPopupShowing():
				api.setNavigatorObject(lastFocusedIntelliSenseItem)
				return
		if self._shouldIgnoreFocusEvent(obj):
			return
		intelliSenseLastFocused = False
		lastFocusedIntelliSenseItem = None
		nextHandler()

	def _isCompletionPopupShowing(self):
		obj = api.getForegroundObject()
		try:
			if obj.firstChild.firstChild.firstChild.next.next.role == controlTypes.ROLE_POPUPMENU:
				return True
		except AttributeError:
			pass
		try:
			obj1 = obj .firstChild
			obj2 = obj1.firstChild
			if (
				obj1.role == controlTypes.ROLE_WINDOW
				and obj1.name == ""
				and obj2.role == controlTypes.ROLE_WINDOW
				and obj2.name == ""
			):
				return True
		except AttributeError:
			pass
		return False

	def _shouldIgnoreFocusEvent(self, obj):
		if (
			(obj.name is None or len(obj.name) == 0)
			and obj.role == controlTypes.ROLE_UNKNOWN
			and obj.windowClassName == "TBToolboxPane"
		):
			# A pane that gets in the way within tool box tool window.
			# Don't report the focus event for this element, a correct focus will follow up
			return True

	# Almost copied from NVDA core with minor modifications
	# Will be removed when NVDA resolve status bar issues
	def script_reportStatusLine(self, gesture):
		# It seems that the status bar is the last child of the forground object, so get it from there
		obj = api.getForegroundObject().lastChild
		found = False
		if obj and obj.role == controlTypes.ROLE_STATUSBAR:
			text = api.getStatusBarText(obj)
			api.setNavigatorObject(obj)
			found = True
		else:
			info = api.getForegroundObject().flatReviewPosition
			if info:
				info.expand(textInfos.UNIT_STORY)
				info.collapse(True)
				info.expand(textInfos.UNIT_LINE)
				text = info.text
				info.collapse()
				api.setReviewPosition(info)
				found = True
		if not found:
			# Translators: Reported when there is no status line for the current program or window.
			ui.message(_("No status line found"))
			return
		if scriptHandler.getLastScriptRepeatCount() == 0:
			ui.message(text)
		else:
			speech.speakSpelling(text)
	# Translators: Input help mode message for report status line text command.
	script_reportStatusLine.__doc__ = _(
		"Reads the current application status bar and moves the navigator to it. If pressed twice, spells the"
		"information."
	)
	script_reportStatusLine.category = SCRCAT_FOCUS

	def script_reportParameterInfo(self, gesture):
		# get the parameter info object
		try:
			obj = api.getForegroundObject().firstChild.firstChild
		except AttributeError:
			return
		if obj.role == controlTypes.ROLE_TOOLTIP:
			# emulate an alert event for this object
			eventHandler.queueEvent("alert", obj)

	__gestures = {
		"kb(desktop):NVDA+End": "reportStatusLine",
		"kb(laptop):NVDA+Shift+End": "reportStatusLine",
		"kb:control+shift+space": "reportParameterInfo"
	}


def _shouldIgnoreEditorAncestorFocusEvents():
	# We don't report focusEntered events for some of the text editor ancestors when last focused object was
	# IntelliSense menu item. This is useful in following cases:
	# * When the user chooses a completion from the intelliSense or when he/she closes this menu
	# * Sometimes when navigating the completion list of intelliSense, the editor fires focus events
	global intelliSenseLastFocused
	return intelliSenseLastFocused


class DocumentTab(UIA):
	"""one of the editor focus ancestors, we ignore focus entered events in some cases
	see _shouldIgnoreEditorAncestorFocusEvents for more info
	"""

	def event_focusEntered(self):
		if _shouldIgnoreEditorAncestorFocusEvents():
			return
		return super().event_focusEntered()


class DocumentGroup(UIA):
	"""one of the editor focus ancestors, we ignore focus entered events in some cases
	see _shouldIgnoreEditorAncestorFocusEvents for more info
	"""

	def event_focusEntered(self):
		if _shouldIgnoreEditorAncestorFocusEvents():
			return
		return super().event_focusEntered()


REG_CUT_POS_INFO = re.compile(r" \d+ of \d+$")
REG_GET_ITEM_INDEX = re.compile(r"^ \d+")
REG_GET_GROUP_COUNT = re.compile(r"\d+$")


class IntelliSenseMenuItem(UIA):

	def _get_states(self):
		states = set()
		# Only fetch the states witch are likely to change. Fetching some states for this view can throw an
		# exception, which causes a latency:
		e = self.UIACachedStatesElement
		try:
			hasKeyboardFocus = e.cachedHasKeyboardFocus
		except COMError:
			hasKeyboardFocus = False
		if hasKeyboardFocus:
			states.add(controlTypes.STATE_FOCUSED)
		# Don't fetch the role unless we must, but never fetch it more than once.
		role = None
		if e.getCachedPropertyValue(UIAHandler.UIA_IsSelectionItemPatternAvailablePropertyId):
			role = self.role
			states.add(
				controlTypes.STATE_CHECKABLE if role == controlTypes.ROLE_RADIOBUTTON
				else controlTypes.STATE_SELECTABLE
			)
			if e.getCachedPropertyValue(UIAHandler.UIA_SelectionItemIsSelectedPropertyId):
				states.add(
					controlTypes.STATE_CHECKED if role == controlTypes.ROLE_RADIOBUTTON
					else controlTypes.STATE_SELECTED
				)
		# those states won't change for this UI element, so add them to the states set
		states.add(controlTypes.STATE_FOCUSABLE)
		states.add(controlTypes.STATE_READONLY)
		return states

	def event_gainFocus(self):
		global intelliSenseLastFocused
		global lastFocusedIntelliSenseItem
		intelliSenseLastFocused = True
		lastFocusedIntelliSenseItem = self
		super().event_gainFocus()

	def _get_name(self):
		# by default, the name of the intelliSense menu item includes the position info, so remove it
		oldName = super().name
		newName = re.sub(REG_CUT_POS_INFO, "", oldName)
		return newName

	def _get_positionInfo(self):
		"""gets the position info of the intelliSense menu item based on the original name
		the user can control whether to have this position info from VS settings dialog
		"""
		if not config.conf["visualStudio"]["reportIntelliSensePosInfo"]:
			return {}
		oldName = super().name
		try:
			positionalInfoStr = re.search(REG_CUT_POS_INFO, oldName).group()
		except Exception:
			return {}
		info = {}
		itemIndex = int(re.search(REG_GET_ITEM_INDEX, positionalInfoStr).group())
		if itemIndex > 0:
			info['indexInGroup'] = itemIndex
		groupCount = int(re.search(REG_GET_GROUP_COUNT, positionalInfoStr).group())
		if groupCount > 0:
			info['similarItemsInGroup'] = groupCount
		return info


class VarsTreeView(IAccessible):
	"""the parent view of the variables view in the locals / autos/ watch/ call stack windows"""

	role = controlTypes.ROLE_TREEVIEW
	name = ''

	def event_focusEntered(self):
		# For some reason, NVDA doesn't execute a focusEntered event for this object, so force it to do so
		speech.speakObject(self, reason=controlTypes.REASON_FOCUSENTERED)


# a regular expression for removing level info from first matching child's value, see _get_positionInfo for
# more info
REG_CUT_LEVEL_INFO = re.compile(r" @ tree depth \d+$")
# a regular expression for getting the level from the first matching child value, see _get_positionInfo for
# more info
REG_GET_LEVEL = re.compile(r"\d+$")


class BadVarView(ContentGenericClient):
	"""the view that showes the variable info (name, value, type) in the locals / autos / watch windows
	also, the call stack window uses this view to expose its info
	accessibility info for this view is retreaved from the children of the parent view.
	the matching children for the view has the focused / selected state. The number of matching children is 3,
	except for the call stack tool window, there, the number of matching children is 2.
	refer to _getMatchingParentChildren method for more info
	"""

	role = controlTypes.ROLE_TREEVIEWITEM
	TextInfo = NVDAObjectTextInfo

	def _getMatchingParentChildren(self):
		parentChildren = self.parent.children
		matchingChildren = []
		for index, child in enumerate(parentChildren):
			if (
				controlTypes.STATE_SELECTED in child.states
				or controlTypes.STATE_FOCUSED in child.states
				and not child.name.startswith("[Column")
			):
				matchingChildren.append(parentChildren[index + 1])
				matchingChildren.append(parentChildren[index + 2])
				if self._isCallStackWindow():
					break
				matchingChildren.append(parentChildren[index + 3])
				break
		return matchingChildren

	def _isCallStackWindow(self):
		try:
			return self.parent.parent.parent.parent.name == "Call Stack"
		except AttributeError:
			return False

	def isDuplicateIAccessibleEvent(self, obj):
		if isinstance(obj, BadVarView):
			return self == obj
		return super().isDuplicateIAccessibleEvent(obj)

	def _get_name(self):
		matchingChildren = self._getMatchingParentChildren()
		if not matchingChildren:
			return None
		if len(matchingChildren) < 2:
			return None
		res = []
		for child in matchingChildren:
			name = child.name
			value = child.value
			# Remove the level info
			value = re.sub(REG_CUT_LEVEL_INFO, "", value)
			res.append(name + ": ")
			res.append(value)
			res.append(", ")
		# Remove last coma
		res.pop(-1)
		return "".join(res)

	def _get_states(self):
		superStates = super().states
		matchingChildren = self._getMatchingParentChildren()
		if matchingChildren is None:
			return superStates
		if len(matchingChildren) == 0:
			return superStates
		states = matchingChildren[0]._get_states() | superStates
		if self.name.startswith("Name: None"):
			# If this happens, then the view has no meaningful info
			states.add(controlTypes.STATE_UNAVAILABLE)
		return states

	def _isEqual(self, other):
		if not isinstance(other, BadVarView):
			return False
		return self is other

	def _get_positionInfo(self):
		# only calculate the level
		# The level is found in the first matching child's value. which is usually the name of the variable
		# Suppose  the view shows info about a var called i, which is not a part of an array, then value string
		# will be as following:
		# i @ tree depth 1
		# Index in group,  similar items in group are not easy to calculate, and it won't be efficient
		matchingChildren = self._getMatchingParentChildren()
		if not matchingChildren:
			return {}
		matchingChildStr = matchingChildren.pop(0).value
		levelStr = re.search(REG_GET_LEVEL, matchingChildStr)
		if levelStr is None:
			return {}
		levelStr = levelStr.group()
		if not levelStr.isdigit():
			return {}
		level = int(levelStr)
		if level <= 0:
			return {}
		info = {}
		info["level"] = level
		return info

	def event_stateChange(self):
		# We don't need to report this event for 2 reasons:
		# * Expand / collapse events is faked with the scripts below, they won't work otherwise
		# * The view is more responsive without reporting this event
		return

	def event_gainFocus(self):
		if not self.hasFocus:
			# Don't report  focus event for this view if the hasFocus property is False. This event is redundant and
			# confusing, and a correct focus event will be fired after this one
			return
		self.parent.firstChild = self
		super().event_gainFocus()

	def event_typedCharacter(self, ch):
		# Default implementation of typedCharacter causes VS and NVDA to crash badly, if the user hits esc while in
		# the quick watch window. The direct reason for the problem is that NVDA tries to get the states for the
		# object to decide whether typing is protected, and it seems the object will be already destroyed in that
		# stage. Only speek typed characters if needed
		if config.conf["keyboard"]["speakTypedCharacters"] and ord(ch) >= 32:
			speech.speakSpelling(ch)
		return

	def script_expand(self, gesture):
		if controlTypes.STATE_COLLAPSED in self.states:
			# Translators: a message indicating that a tree view item in watch/locals/... has been expanded
			ui.message(_("expanded"))
		gesture.send()

	def script_collapse(self, gesture):
		if controlTypes.STATE_EXPANDED in self.states:
			# Translators: a message indicating that a tree view item in watch/locals/... has been collapsed
			ui.message(_("collapsed"))
		gesture.send()

	__gestures = {
		"kb:leftArrow": "collapse",
		"kb:rightArrow": "expand"
	}


class VSMenuItem(UIA):
	"""ordinary menu items in visual studio"""

	def _get_states(self):
		states = super()._get_states()
		# Visual studio exposes the menu item which has a sub menu as collapsed/ expanded
		# add HASPOPup state to fix NVDA behavior when this state is present
		if controlTypes.STATE_COLLAPSED in states or controlTypes.STATE_EXPANDED in states:
			states.add(controlTypes.STATE_HASPOPUP)
		# This state is redundant in this context, it causes NVDA to say "not checked" for each menu item
		states.discard(controlTypes.STATE_CHECKABLE)
		return states

	def _get_keyboardShortcut(self):
		# This method is redundant for NVDA 16.3 and newer. However, we need it for older versions of NVDA
		ret = ""
		try:
			ret += self.UIAElement.currentAccessKey
		except COMError:
			pass
		if ret != "":
			# Add a double space to the end of the string
			ret += "  "
		try:
			ret += self.UIAElement.currentAcceleratorKey
		except COMError:
			pass
		return ret


# Regular expression to get line info text from the entire status bar text
REG_GET_LINE_TEXT = re.compile(r"Ln \d+")
# A regular expression to get line number from line info text in the status bar
REG_GET_LINE_NUM = re.compile(r"\d+$")


def _getCurLineNumber():
	"""gets current line number which has the caret in the editor based on status bar text"""
	obj = api.getForegroundObject().lastChild
	text = None
	if obj and obj.role == controlTypes.ROLE_STATUSBAR:
		text = api.getStatusBarText(obj)
	if not text:
		return 0
	try:
		lineInfo = re.search(REG_GET_LINE_TEXT, text).group()
	except Exception:
		return 0
	try:
		lineNum = int(re.search(REG_GET_LINE_NUM, lineInfo).group())
	except Exception:
		return 0
	if lineNum <= 0:
		return 0
	return lineNum


REG_GET_BREAKPOINT_STATE = re.compile("Enabled|Disabled")


class Breakpoint(UIA):
	"""a class for break point control to allow us to detect and report break points once the caret reaches a
	line with break point"""

	def event_nameChange(self):
		# A nameChange event is fired by breakpoint UI control when the caret reaches a line with breakpoint, so,
		# we rely on this to announce breakpoints
		global caretMovedToDifferentLine
		if not caretMovedToDifferentLine:
			# A nameChange event can be fired multiple times when moving by character within the same line, so, return
			# if we already announced the break point for the current line
			return
		caretMovedToDifferentLine = False
		currentLineNum = _getCurLineNumber()
		BPLineNum = self._getLineNumber()
		if (
			currentLineNum == 0
			or BPLineNum == 0
			or currentLineNum != BPLineNum
		):
			return
		if config.conf["visualStudio"]["beepOnBreakpoints"]:
			tones.beep(1000, 50)
		if not config.conf["visualStudio"]["announceBreakpoints"]:
			return
		message = _("breakpoint")
		state = re.search(REG_GET_BREAKPOINT_STATE, self.name)
		if state:
			message += "  "
			message += state.group()
		ui.message(message)

	def _getLineNumber(self):
		"""gets the line number of the breakpoint based on the automation ID"""
		try:
			ret = self.UIAElement.CachedAutomationID
		except COMError:
			return 0
		try:
			lineNum = int(re.search(REG_GET_LINE_NUM, ret).group())
		except Exception:
			return 0
		if lineNum <= 0:
			return 0
		return lineNum


class TextEditor(WpfTextView):
	"""
	We need this class to try to tell whether the caret has moved to a different line, this helps us to not make
	several announcements of the same breakpoint when moving the caret by character left and rite on the same
	line. Also, commands for navigating the code with the debugger now causes NVDA to report the line.
	"""

	description = ""

	def script_caret_moveByLine(self, gesture):
		global caretMovedToDifferentLine
		caretMovedToDifferentLine = True
		super().script_caret_moveByLine(gesture)

# This method is only a work around til the bug with compareing UIA bookmarks is resolved
# We need to bind debugger stepping commands to  moveByLine script only
	def script_debugger_step(self, gesture):
		global caretMovedToDifferentLine
		caretMovedToDifferentLine = True
		try:
			info = self.makeTextInfo(textInfos.POSITION_CARET)
		except COMError:
			log.debug("exception")
			gesture.send()
			return
		bookmark = info.bookmark
		gesture.send()
		for i in range(4):
			caretMoved, newInfo = self._hasCaretMoved(bookmark)
		if not caretMoved:
			log.debug("caret move failed")
		self._caretScriptPostMovedHelper(textInfos.UNIT_LINE, gesture, newInfo)

	__gestures = {
		"kb:f10": "debugger_step",
		"kb:f11": "debugger_step",
		"kb:f5": "debugger_step",
		"kb:shift+f11": "debugger_step"
	}


# A regular expression to split the error list menu item name to columns
REG_SPLIT_ERROR = re.compile("(Severity:.*)(Code:.*)(Description:.*\r?\n?.*)(Project:.*)(File:.*)(Line:.*)")
# A regular expression to split the error list menu item name to columns when no code column is available
REG_SPLIT_ERROR_NO_CODE_COL = re.compile(
	"(Severity:.*)(Description:.*\r?\n?.*)(Project:.*)(File:.*)(Line:.*)"
)
# A regular expression to split the error list menu item name to columns when no file column is available
REG_SPLIT_ERROR_NO_FILE_COL = re.compile(
	"(Severity:.*)(Code:.*)(Description:.*\r?\n?.*)(Project:.*)(Line:.*)"
)
# A regular expression to split the error list menu item name to columns when no line column is available
REG_SPLIT_ERROR_NO_LINE_COL = re.compile(
	"(Severity:.*)(Code:.*)(Description:.*\r?\n?.*)(Project:.*)(File:.*)"
)


class ErrorsListItem(RowWithoutCellObjects, RowWithFakeNavigation, UIA):
	"""
	A class for list item of the errors list. The goal is to enable the user to navigate each row with NVDA's
	commands for navigating tables (ctrl+alt+right/left arrow). In addition, it is possible to move directly to
	a column with ctrl + alt + number, where the number is the column number we wish to move to
	"""

	def _getColumnContent(self, column):
		children = self.children
		try:
			return children[column - 1].firstChild.name
		except Exception as e:
			log.debug(e)
		return ""

	def _getColumnHeader(self, column):
		text = self._getColumnContentAndHeader(column)
		# extract the header
		text = text.split(":", 1)[0]
		# Remove spaces if there are any
		text = text.strip()
		return text

	def _getColumnContentAndHeader(self, column):
		if column < 1 or column > self.childCount:
			return ""
		try:
			return re.search(REG_SPLIT_ERROR, self.name).group(column)
		except IndexError:
			pass
		try:
			return re.search(REG_SPLIT_ERROR_NO_CODE_COL, self.name).group(column)
		except IndexError:
			pass
		try:
			return re.search(REG_SPLIT_ERROR_NO_FILE_COL, self.name).group(column)
		except IndexError:
			pass
		try:
			return re.search(REG_SPLIT_ERROR_NO_LINE_COL, self.name).group(column)
		except IndexError:
			pass
		return ""

	def _getColumnLocation(self, column):
		if column < 1 or column > self.childCount:
			return None
		child = None
		try:
			child = self.children[column - 1].firstChild
		except Exception as e:
			log.debug(e)
		if not child:
			return None
		return child.location

	def _get_childCount(self):
		return len(super().children)

	def initOverlayClass(self):
		for i in range(1, self.childCount + 1):
			self.bindGesture("kb:control+alt+%d" % i, "moveToColumn")

	def script_moveToColumn(self, gesture):
		keyName = gesture.displayName
		# extract the number from the key name
		columnNum = re.search(r"\d+$", keyName).group()
		columnNum = int(columnNum)
		self._moveToColumnNumber(columnNum)


class QuickInfoToolTip(Toast):
	"""
	Quick info toast, the goal is to get this view to be considered as toast by NVDA, so it will be reported
	when it fires an alert event.
	"""

	def _get_name(self):
		return "Quick Info"

	def _get_description(self):
		# This view has a long description, don't think the user wants to hear it every tiem he invokes the
		# quick info
		return ""


class ParameterInfo (Toast):
	role = controlTypes.ROLE_TOOLTIP

	def _get_description(self):
		return ""


class ToolboxItem(IAccessible):
	"""the tool box item view in the tool box tool windo"""

	role = controlTypes.ROLE_TREEVIEWITEM

	def event_gainFocus(self):
		badStates = {controlTypes.STATE_INVISIBLE, controlTypes.STATE_UNAVAILABLE, controlTypes.STATE_OFFSCREEN}
		if badStates.issubset(self.states) or controlTypes.STATE_SELECTED not in self.states:
			# If the object has those states, or the object don't has a selected state, don't report this invalid
			# focus event.
			# A valid focus event will be fired after then.
			return
		super().event_gainFocus()

	def event_stateChange(self):
		# No need to report state change for this object for the following reasons:
		# * On expand / collaps: a focus event is fired
		# * A state change event is fired when moving between tool box items, and causes NVDA to announce
		# 	"not available" each time
		return

	def _get_value(self):
		# The value is exposed as level info, don't report it
		return

	def _get_positionInfo(self):
		info = {}
		level = super().value
		# The level is zero based, unlike NVDA's convention of 1 based level, so, fix it.
		level = int(level)
		level += 1
		info["level"] = level
		return info


class SwitcherDialog(IAccessible):
	"""the view of the file / tool windows switcher which is used to move between opened files and active tool
	windows. In latest version of VS (2015 currently), only gainFocus event method is needed to report the first
	selected entry when a file is opened. In older versions, this overlay class manages all the user interaction
	with this view. AKA moving between entries using the corresponding keyboard commands
	"""

	def initOverlayClass(self):
		# All entries of the dialog (active files and active tool windows entries)
		self.entries = []
		# Whether a focus entered event should be fired to the active files list
		self.shouldFireFocusEnteredEventFiles = True
		# Whether a focus entered event should be fired to the active tool windows  list
		self.shouldFireFocusEnteredEventTools = True

	def event_gainFocus(self):
		# Add active files entries
		try:
			self.entries.extend(self.children[1].children)
		except IndexError:
			# No active files
			pass

		# Add active tool windows entries
		try:
			self.entries.extend(self.children[0].children)
		except IndexError:
			# No active tool windows, this should not happen never
			pass
		self._reportSelectedEntry()

	def _getSelectedEntry(self):
		for entry in self.entries:
			if controlTypes.STATE_SELECTED in entry.states:
				return entry
		return None

	def _reportSelectedEntry(self):
		obj = self._getSelectedEntry()
		if obj is None:
			return
		self._reportFocusEnteredEventForParent(obj)
		api.setNavigatorObject(obj)
		obj.reportFocus()

	def _reportFocusEnteredEventForParent(self, obj):
		"""checks if we need to fire a focusEntered event for the selected entry's parent, and fires an event
		if we need to"""
		if obj.parent.name == "Active Files" and self.shouldFireFocusEnteredEventFiles:
			eventHandler.executeEvent("focusEntered", obj.parent)
			self.shouldFireFocusEnteredEventFiles = False
			self.shouldFireFocusEnteredEventTools = True
		if obj.parent.name == "Active Tool Windows" and self.shouldFireFocusEnteredEventTools:
			eventHandler.executeEvent("focusEntered", obj.parent)
			self.shouldFireFocusEnteredEventFiles = True
			self.shouldFireFocusEnteredEventTools = False

	def script_onEntryChange(self, gesture):
		gesture.send()
		studioVersion = self.appModule.productVersion[:2]
		studioVersion = int(studioVersion)
		if studioVersion >= 14:
			# If VS 2015 or higher is the  version used, then don't do any thing, a correct focus event will be fired,
			# and the control will move to the focused view.
			return
		self._reportSelectedEntry()

	__gestures = {
		"kb:control+downArrow": "onEntryChange",
		"kb:control+upArrow": "onEntryChange",
		"kb:control+leftArrow": "onEntryChange",
		"kb:control+rightArrow": "onEntryChange",
		"kb:control+tab": "onEntryChange",
		"kb:control+shift+tab": "onEntryChange"
	}


REG_SPLIT_LOCATION_TEXT = re.compile(r"(\d+), (\d+) (\d+), (\d+)")


class FormsComponent(IAccessible):
	"""the UI component in windows forms designer """

	def script_onSizeChange(self, gesture):
		gesture.send()
		# Get the position from the status bar
		obj = api.getForegroundObject().lastChild
		text = obj.children[2].name
		width = re.match(REG_SPLIT_LOCATION_TEXT, text).group(3)
		hight = re.match(REG_SPLIT_LOCATION_TEXT, text).group(4)
		# Translators: the width and the hight of a UI element in windows forms designer
		msg = _("width: %s  hight: %s" % (width, hight))
		ui.message(msg)

	def script_onLocationChange(self, gesture):
		gesture.send()
		# Get the location from the status bar
		obj = api.getForegroundObject().lastChild
		text = obj.children[2].name
		x = re.match(REG_SPLIT_LOCATION_TEXT, text).group(1)
		y = re.match(REG_SPLIT_LOCATION_TEXT, text).group(2)
		# Translators: the x coord and the y coord of a UI element in windows forms designer
		msg = _("X: %s  y: %s" % (x, y))
		ui.message(msg)

	__gestures = {
		"kb:shift+upArrow": "onSizeChange",
		"kb:shift+downArrow": "onSizeChange",
		"kb:shift+rightArrow": "onSizeChange",
		"kb:shift+leftArrow": "onSizeChange",
		"kb:control+upArrow": "onLocationChange",
		"kb:control+downArrow": "onLocationChange",
		"kb:control+rightArrow": "onLocationChange",
		"kb:control+leftArrow": "onLocationChange",
		"kb:upArrow": "onLocationChange",
		"kb:downArrow": "onLocationChange",
		"kb:leftArrow": "onLocationChange",
		"kb:rightArrow": "onLocationChange"
	}


class EditorAncestor(UIA):
	"""an ancestor of the code editor, we need this because this control returns true incorrectly when comparing
	it with other instance of the same type. This causes NVDA to not execute focus entered events when it should
	do. The issue is present when using ctrl + f6 / ctrl + shift + f6 to move between openned code editors."""

	def _isEqual(self, other):
		return False


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
