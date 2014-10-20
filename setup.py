#!/usr/bin/env python
#
# $Id: /work/modules/aggdraw/setup.py 1180 2006-02-12T14:24:26.234348Z Fredrik  $
# Setup script for aggdraw
#
# Usage:
#
#   To build in current directory:
#   $ python setup.py build_ext -i
#
#   To build and install:
#   $ python setup.py install
#

from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext
from distutils import sysconfig
import platform as plat

import os, sys, struct, string, re

VERSION = "1.2a4"

SUMMARY="High quality drawing interface for PIL."

DESCRIPTION = """\

The aggdraw module implements the basic WCK 2D Drawing Interface on
top of the AGG library. This library provides high-quality drawing,
with anti-aliasing and alpha compositing, while being fully compatible
with the WCK renderer.

"""

# pointer to freetype build directory (tweak as necessary)
FREETYPE_ROOT = None

sources = [
    # source code currently used by aggdraw
    # FIXME: link against AGG library instead?
    "agg2/src/agg_arc.cpp",
    "agg2/src/agg_bezier_arc.cpp",
    "agg2/src/agg_curves.cpp",
    "agg2/src/agg_path_storage.cpp",
    "agg2/src/agg_rasterizer_scanline_aa.cpp",
    "agg2/src/agg_trans_affine.cpp",
    "agg2/src/agg_vcgen_contour.cpp",
    # "agg2/src/agg_vcgen_dash.cpp",
    "agg2/src/agg_vcgen_stroke.cpp",
    ]

defines = []
include_dirs = ["agg2/include"]
library_dirs = []
libraries = []

try:
    # add necessary to distutils (for backwards compatibility)
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None
    DistributionMetadata.platforms = None
except:
    pass

def add_directory(path, dir, where=None):
    if dir and os.path.isdir(dir) and dir not in path:
        if where is None:
            path.append(dir)
        else:
            path.insert(where, dir)

def find_include_file(self, include):
    for directory in self.compiler.include_dirs:
        if os.path.isfile(os.path.join(directory, include)):
            return True
    return False

def find_library_file(self, library):
    return self.compiler.find_library_file(self.compiler.library_dirs, library)

def find_version(filename):
    for line in open(filename).readlines():
        m = re.search("VERSION\s*=\s*\"([^\"]+)\"", line)
        if m:
            return m.group(1)
    return None

class agg_build_ext(build_ext):
    def build_extensions(self):
        #
        # add platform directories

        if sys.platform == "cygwin":
            # pythonX.Y.dll.a is in the /usr/lib/pythonX.Y/config directory
            add_directory(library_dirs, os.path.join(
                "/usr/lib", "python%s" % sys.version[:3], "config"))

        elif sys.platform == "darwin":
            # attempt to make sure we pick freetype2 over other versions
            add_directory(include_dirs, "/sw/include/freetype2")
            add_directory(include_dirs, "/sw/lib/freetype2/include")
            # fink installation directories
            add_directory(library_dirs, "/sw/lib")
            add_directory(include_dirs, "/sw/include")
            # darwin ports installation directories
            add_directory(library_dirs, "/opt/local/lib")
            add_directory(include_dirs, "/opt/local/include")
            # freetype2 ships with X11
            add_directory(library_dirs, "/usr/X11/lib")
            add_directory(include_dirs, "/usr/X11/include")
            # if homebrew is installed, use its lib and include directories
            import subprocess
            try:
                prefix = subprocess.check_output(['brew', '--prefix'])
                if prefix:
                    prefix = prefix.strip()
                    add_directory(library_dirs, os.path.join(prefix, 'lib'))
                    add_directory(include_dirs, os.path.join(prefix, 'include'))
            except:
                pass # homebrew not installed

        elif sys.platform.startswith("linux"):
            for platform_ in (plat.processor(), plat.architecture()[0]):

                if not platform_:
                    continue

                if platform_ in ["x86_64", "64bit"]:
                    add_directory(library_dirs, "/lib64")
                    add_directory(library_dirs, "/usr/lib64")
                    add_directory(library_dirs, "/usr/lib/x86_64-linux-gnu")
                    break
                elif platform_ in ["i386", "i686", "32bit"]:
                    add_directory(library_dirs, "/usr/lib/i386-linux-gnu")
                    break
            else:
                raise ValueError(
                    "Unable to identify Linux platform: `%s`" % platform_)

            # XXX Kludge. Above /\ we brute force support multiarch. Here we
            # try Barry's more general approach. Afterward, something should
            # work ;-)
            self.add_multiarch_paths()

        add_directory(library_dirs, "/usr/local/lib")

        prefix = sysconfig.get_config_var("prefix")
        if prefix:
            add_directory(library_dirs, os.path.join(prefix, "lib"))
            add_directory(include_dirs, os.path.join(prefix, "include"))

        #
        # add configured kits
        if isinstance(FREETYPE_ROOT, tuple):
            lib_root, include_root = FREETYPE_ROOT
        else:
            lib_root = include_root = FREETYPE_ROOT
        add_directory(library_dirs, lib_root)
        add_directory(include_dirs, include_root)

        #
        # add standard directories
        # standard locations
        add_directory(library_dirs, "/usr/local/lib")
        add_directory(include_dirs, "/usr/local/include")

        add_directory(library_dirs, "/usr/lib")
        add_directory(include_dirs, "/usr/include")

        #
        # insert new dirs *before* default libs, to avoid conflicts
        # between Python PYD stub libs and real libraries

        self.compiler.library_dirs = library_dirs + self.compiler.library_dirs
        self.compiler.include_dirs = include_dirs + self.compiler.include_dirs

        #
        # look for available libraries

        class feature:
            freetype = None
        feature = feature()

        if find_library_file(self, "freetype"):
            # look for freetype2 include files
            freetype_version = 0
            for dir in self.compiler.include_dirs:
                if os.path.isfile(os.path.join(dir, "ft2build.h")):
                    freetype_version = 21
                    dir = os.path.join(dir, "freetype2")
                    break
                dir = os.path.join(dir, "freetype2")
                if os.path.isfile(os.path.join(dir, "ft2build.h")):
                    freetype_version = 21
                    break
                if os.path.isdir(os.path.join(dir, "freetype")):
                    freetype_version = 20
                    break
            if freetype_version:
                feature.freetype = "freetype"
                feature.freetype_version = freetype_version
                if dir:
                    add_directory(self.compiler.include_dirs, dir, 0)

        libs = []
        if sys.platform == "win32":
            libs.extend(["kernel32", "user32", "gdi32"])
        if struct.unpack("h", "\0\1")[0] == 1:
            defines.append(("WORDS_BIGENDIAN", None))

        #
        # additional libraries
        if feature.freetype:
            sources.append("agg2/font_freetype/agg_font_freetype.cpp")
            include_dirs.append("agg2/font_freetype")
            libraries.append("freetype")

            defines.append(("HAVE_FREETYPE2", None))
            if feature.freetype_version == 20:
                defines.append(("USE_FREETYPE_2_0", None))
        build_ext.build_extensions(self)

        #
        # sanity and security checks
        self.summary_report(feature)

    def summary_report(self, feature):

        print "-" * 68
        print "AGGDRAW", VERSION, "SETUP SUMMARY"
        print "-" * 68
        print "version      ", VERSION
        v = string.split(sys.version, "[")
        print "platform     ", sys.platform, string.strip(v[0])
        for v in v[1:]:
            print "             ", string.strip("[" + v)
        print "-" * 68

        options = [
            (feature.freetype, "FREETYPE2"),
            ]

        all = True
        for option in options:
            if option[0]:
                print "---", option[1], "support available"
            else:
                print "***", option[1], "support not available",
                print
                all = False

        if not all:
            print "To add a missing option, make sure you have the required"
            print "library, and set the corresponding ROOT variable in the"
            print "setup.py script."
            print

        print "To check the build, run the selftest.py script."


    # http://hg.python.org/users/barry/rev/7e8deab93d5a
    def add_multiarch_paths(self):
        # Debian/Ubuntu multiarch support.
        # https://wiki.ubuntu.com/MultiarchSpec
        # self.build_temp
        tmpfile = os.path.join(self.build_temp, 'multiarch')
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        ret = os.system(
            'dpkg-architecture -qDEB_HOST_MULTIARCH > %s 2> /dev/null' %
            tmpfile)
        try:
            if ret >> 8 == 0:
                fp = open(tmpfile, 'r')
                multiarch_path_component = fp.readline().strip()
                add_directory(
                    self.compiler.library_dirs,
                    '/usr/lib/' + multiarch_path_component)
                add_directory(
                    self.compiler.include_dirs,
                    '/usr/include/' + multiarch_path_component)
        finally:
            os.unlink(tmpfile)


setup(
    name="aggdraw",
    version=VERSION,
    author="Fredrik Lundh",
    author_email="fredrik@pythonware.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        # "Development Status :: 5 - Production/Stable",
        "Topic :: Multimedia :: Graphics",
        ],
    cmdclass = {"build_ext": agg_build_ext},
    description=SUMMARY,
    download_url="http://www.effbot.org/downloads#aggdraw",
    license="Python (MIT style)",
    long_description=DESCRIPTION.strip(),
    platforms="Python 2.1 and later.",
    url="http://www.effbot.org/zone/aggdraw.htm",
    ext_modules = [
        Extension("aggdraw", ["aggdraw.cxx"] + sources,
                  define_macros=defines,
                  include_dirs=include_dirs,
                  library_dirs=library_dirs, libraries=libraries
                  )
        ]
    )
