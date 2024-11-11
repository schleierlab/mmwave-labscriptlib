import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))

project = 'mmwave-labscript'
copyright = '2024, Michelle Wu, Lin Xin, Nolan Peard, Sam Cohen, Tony Zhang'
author = 'Nolan Peard'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

autodoc_mock_imports = ['labscript', 'labscript_devices', 'PyQt5', 'qtutils',
                        'imp', 'user_devices.NI_PXIe_6363',
                        'user_devices.NI_PXIe_6739', 'user_devices.manta419b',
                        'user_devices.spcm', 'user_devices.DDS',
                        'user_devices.kinetix', 'labscriptlib.shot_globals',
                        'runmanager', 'labscriptlib']

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None