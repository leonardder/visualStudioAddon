# appModule for visual studio
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2016-2019 Mohammad Suliman, Leonard de Ruijter, https://github.com/leonardder/visualStudioAddon

import addonHandler
from NVDAObjects.UIA import Toast_win8 as Toast
from NVDAObjects.UIA import UIA, WpfTextView
import controlTypes


class TextEditor(WpfTextView):
	pass


class ParameterInfo (Toast):
	role = controlTypes.ROLE_TOOLTIP

	def _get_description(self):
		return ""
