#!/usr/bin/python

import ConfigParser
import os.path
import sys
import time

import backend
import logger
import terminal
import util

from constants import *

class Naoki(object):
	def __init__(self):
		# First, setup the logging
		self.logging = logger.Logging(self)

		# Second, parse the command line options
		self.cli = terminal.Commandline(self)

		self.log.debug("Successfully initialized naoki instance")
		for k, v in config.items():
			self.log.debug("    %s: %s" % (k, v))

	def run(self):
		args = self.cli.args

		# If there is no action provided, exit
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"build" : self.call_build,
			"toolchain" : self.call_toolchain,
			"package" : self.call_package,
			"source" : self.call_source,
		}

		return actionmap[args.action.name](args.action)

	def call_toolchain(self, args):
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"build" : self.call_toolchain_build,
			"download" : self.call_toolchain_download,
			"tree" : self.call_toolchain_tree,
		}

		return actionmap[args.action.name](args.action)

	def call_toolchain_build(self, args):
		toolchain = chroot.Toolchain(arches.current["name"])

		return toolchain.build()

	def call_toolchain_download(self, args):
		toolchain = chroot.Toolchain(arches.current["name"])

		return toolchain.download()

	def call_toolchain_tree(self, args):
		print backend.deptree(backend.parse_package(backend.get_package_names(toolchain=True), toolchain=True))

	def call_build(self, args):
		force = True

		if args.packages == ["all"]:
			force = False
			package_names = backend.get_package_names()
		else:
			package_names = args.packages

		packages = []
		for package in backend.parse_package(package_names, naoki=self):
			if not force and package.built:
				self.log.warn("Skipping %s which was already built" % package.name)

			packages.append(package)

		if len(packages) >= 2:
			packages_sorted = backend.depsort(packages)
			if packages_sorted != packages:
				self.log.warn("Packages were resorted for build: %s" % packages_sorted)
				packages = packages_sorted

		for i in range(0, len(packages)):
			package = packages[i]
			if not package.buildable:
				for dep in package.dependencies_unbuilt:
					if not dep in packages[:i]:
						self.log.error("%s is currently not buildable" % package.name)
						self.log.error("  The package requires these packages to be built first: %s" \
							% [dep.name for dep in package.dependencies_unbuilt])
						return

		for package in packages:
			package.download()

		for package in packages:
			environ = chroot.Environment(package)
			
			if not environ.toolchain.exists:
				self.log.error("You need to build or download a toolchain first.")
				continue

			environ.build()

	def call_package(self, args):
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"info" : self.call_package_info,
			"list" : self.call_package_list,
			"tree" : self.call_package_tree,
			"groups" : self.call_package_groups,
		}

		return actionmap[args.action.name](args.action)

	def call_package_info(self, args):
		for package in backend.parse_package_info(args.packages):
			if args.wiki:
				print package.fmtstr("""\
====== %(name)s ======
| **Version:**  | %(version)s  |
| **Release:**  | %(release)s  |
| **Group:**  | %(group)s  |
| **License:**  | %(license)s  |
| **Maintainer:**  | %(maintainer)s |
| **Dependencies:** | %(deps)s |
| **Build dependencies:** | %(build_deps)s |
| %(summary)s ||
| %(description)s ||
| **Website:**  | %(url)s  |
""")
				continue

			if args.long:
				print package.fmtstr("""\
--------------------------------------------------------------------------------
Name          : %(name)s
Version       : %(version)s
Release       : %(release)s

  %(summary)s

%(description)s

Maintainer    : %(maintainer)s
License       : %(license)s

Files         : %(files)s
Objects       : %(objects)s
Patches       : %(patches)s
--------------------------------------------------------------------------------\
""")
			else:
				print package.fmtstr("""\
--------------------------------------------------------------------------------
Name          : %(name)s
Version       : %(version)s
Release       : %(release)s

  %(summary)s

--------------------------------------------------------------------------------\
""")

	def call_package_list(self, args):
		for package in backend.parse_package_info(backend.get_package_names()):
			if args.long:
				print package.fmtstr("%(name)-32s | %(version)-15s | %(summary)s")
			else:
				print package.fmtstr("%(name)s")

	def call_package_tree(self, args):
		print backend.deptree(backend.parse_package(backend.get_package_names()))

	def call_package_groups(self, args):
		groups = backend.get_group_names()
		if args.wiki:
			print "====== All available groups of packages ======"
			for group in groups:
				print "===== %s =====" % group
				for package in backend.parse_package_info(backend.get_package_names()):
					if not package.group == group:
						continue

					print package.fmtstr("  * [[.package:%(name)s|%(name)s]] - %(summary)s")

		else:
			print "\n".join(groups)

	def call_source(self, args):
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"download" : self.call_source_download,
			"upload" : self.call_source_upload,
			"clean" : self.call_source_clean,
		}

		return actionmap[args.action.name](args.action)

	def call_source_download(self, args):
		for package in backend.parse_package(args.packages or \
				backend.get_package_names(), naoki=self):
			package.download()

	def call_source_upload(self, args):
		pass # TODO

	def call_source_clean(self, args):
		self.log.info("Remove all unused files")
		files = os.listdir(TARBALLDIR)
		for package in backend.parse_package_info(backend.get_package_names()):
			for object in package.objects:
				if object in files:
					files.remove(object)

		for file in sorted(files):
			self.log.info("Removing %s..." % file)
			os.remove(os.path.join(TARBALLDIR, file))

	def _build(self, packages, force=False):
		requeue = []
		packages = package.depsort(packages)
		while packages:
			# Get first package that is to be done
			build = chroot.Environment(packages.pop(0))
			
			if not build.toolchain.exists:
				self.log.error("You need to build or download a toolchain first.")
				return
			
			if build.package.isBuilt:
				if not force:
					self.log.info("Skipping already built package %s..." % build.package.name)
					continue
				self.log.warn("Package is already built. Will overwrite.")
			
			if not build.package.canBuild:
				self.log.warn("Cannot build package %s." % build.package.name)
				if not self.packages:
					self.log.error("Blah")
					return
				self.log.warn("Requeueing. %s" % build.package.name)
				self.packages.append(build.package)
				continue

			self.log.info("Building %s..." % build.package.name)
			build.build()
