#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Script that releases a new version of the software.'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from releaser import Releaser          # easy_install -UZ releaser
from releaser.steps import *
from releaser.git_steps import *

# These settings are used by multiple release steps below.
config = dict(
    github_user='nandoflorestan',  # TODO infer from .git/config
    github_repository='kajiki',
    branch='master',  # Only release new versions in this git branch
    changes_file='CHANGES.rst',
    version_file='kajiki/version.py',  # The version number is in this file
    version_keyword='release',         # Part of the variable name in that file
    log_file='release.log.utf-8.tmp',
    verbosity='info',  # debug | info | warn | error
)

# You can customize your release process below.
# Comment out any steps you don't desire and add your own steps.
Releaser(config,
    Shell('python setup.py test'),  # First of all ensure tests pass
    # CheckRstFiles,  # Documentation: recursively verify ALL .rst files, or:
    CheckRstFiles('README.rst', 'CHANGES.rst', 'LICENSE.rst'),  # just a few.
    # TODO IMPLEMENT CompileAndVerifyTranslations,
    # TODO IMPLEMENT BuildSphinxDocumentation,
    # TODO IMPLEMENT Tell the user to upload the built docs (give URL)
    EnsureGitClean,   # There are no uncommitted changes in tracked files.
    EnsureGitBranch,  # I must be in the branch specified in config
    InteractivelyApproveDistribution,  # Generate sdist, let user verify it
    InteractivelyEnsureChangesDocumented,     # Did you update CHANGES.rst?
    CheckTravis,  # We run this late, so travis-ci has more time to build

    # =================  All checks pass. RELEASE!  ===========================
    SetVersionNumberInteractively,  # Ask for version and write to source code
    # TODO IMPLEMENT CHANGES file: add heading for current version (below dev)
    GitCommitVersionNumber,
    GitTag,  # Locally tag the current commit with the new version number
    PypiRegister,  # Creates the new release at http://pypi.python.org
    PypiUpload,  # Uploads a source distribution to http://pypi.python.org

    # ===========  Post-release: set development version and push  ============
    SetFutureVersion,  # Writes incremented version, now with 'dev' suffix
    GitCommitVersionNumber('future_version',
                           msg='Bump version to {0} after release'),
    GitPush,  # Cannot be undone. If successful, previous steps won't roll back
    GitPushTags,
).release()
