# -*- coding: UTF-8 -*-

# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

import os.path


def _(x):
	return x


# Add-on information variables
addon_info = {
	"addon_name": "visualStudio",
	# Translators: Summary for this add-on to be shown on installation and add-on information.
	"addon_summary": _("Extended support for Visual Studio"),
	# Translators: Long description to be shown for this add-on on add-on information from add-ons manager
	"addon_description": _(
		"This add-on aims to resolve some issues with visual studio, and to enhance the user experience while "
		"using NVDA. Please refer to the help seqtion to get the list of fixes and enhancements this add-on offers."
	),
	# version
	"addon_version": "2019.10",

	"addon_author": ", ".join((
		"Mohammad Suliman <mohmad.s93@gmail.com>",
		"Leonard de Ruijter <alderuijter@gmail.com>",
		"Francisco Del Roio <francipvb@hotmail.com>"
	)),
	# URL for the add-on documentation support
	"addon_url": "https://github.com/leonardder/visualStudioAddon",
	# Documentation file name
	"addon_docFileName": "readme.html",
	# Minimum NVDA version supported (e.g. "2018.3.0", minor version is optional)
	"addon_minimumNVDAVersion": "2019.3",
	# Last NVDA version supported/tested (e.g. "2018.4.0", ideally more recent than minimum version)
	"addon_lastTestedNVDAVersion": "2019.3",

}


# Define the python files that are the sources of your add-on.
# You can use glob expressions here, they will be expanded.
pythonSources = [os.path.join("addon", "appModules", "*.py")]
# Files that contain strings for translation. Usually your python sources
i18nSources = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory, not to the root directory of your addon sources.
excludedFiles = []
