#!/usr/bin/env python

"""Script that releases a new version of the software."""

from releaser import Releaser  # easy_install -UZ releaser
from releaser.git_steps import *
from releaser.steps import *

# These settings are used by multiple release steps below.
config = dict(
    github_user="jackrosenthal",  # TODO infer from .git/config
    github_repository="kajiki",
    branch="master",  # Only release new versions in this git branch
    changes_file="CHANGES.rst",
    version_file="kajiki/version.py",  # The version number is in this file
    version_keyword="release",  # Part of the variable name in that file
    log_file="release.log.utf-8.tmp",
    verbosity="info",  # debug | info | warn | error
)

# You can customize your release process below.
# Comment out any steps you don't desire and add your own steps.
Releaser(
    config,
    Shell("pytest"),  # First of all ensure tests pass
    # CheckRstFiles,  # Documentation: recursively verify ALL .rst files, or:
    # CheckRstFiles('CHANGES.rst', 'LICENSE.rst'),  # just a few.
    # TODO IMPLEMENT CompileAndVerifyTranslations,
    # TODO IMPLEMENT BuildSphinxDocumentation,
    # TODO IMPLEMENT Tell the user to upload the built docs (give URL)
    EnsureGitClean,  # There are no uncommitted changes in tracked files.
    EnsureGitBranch,  # I must be in the branch specified in config
    InteractivelyEnsureChangesDocumented,  # Did you update CHANGES.rst?
    # =================  All checks pass. RELEASE!  ===========================
    SetVersionNumberInteractively,  # Ask for version and write to source code
    # TODO IMPLEMENT CHANGES file: add heading for current version (below dev)
    GitCommitVersionNumber,
    GitTag,  # Locally tag the current commit with the new version number
    InteractivelyApproveDistribution,  # Generate sdist, let user verify it
    InteractivelyApproveWheel,  # Generate wheel, let user verify it
    PypiUpload,  # Make and upload a source .tar.gz to https://pypi.org
    PypiUploadWheel,  # Make and upload source wheel to https://pypi.org
    # ===========  Post-release: set development version and push  ============
    SetFutureVersion,  # Writes incremented version, now with 'dev' suffix
    GitCommitVersionNumber("future_version", msg="Bump version to {0} after release"),
    GitPush,  # Cannot be undone. If successful, previous steps won't roll back
    GitPushTags,
).release()
