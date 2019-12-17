# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter, https://github.com/leonardder/visualStudioAddon

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
from .guiPanel import VSSettingsPanel
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
