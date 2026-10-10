import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import conventional_commits


class ConventionalCommitsTest(unittest.TestCase):
    def test_sync_merge_is_ignored_but_its_commits_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", directory, *args], text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()

            git("init", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            git("commit", "--allow-empty", "-m", "chore: initial")
            base = git("rev-parse", "HEAD")
            git("checkout", "-b", "upstream")
            git("commit", "--allow-empty", "-m", "fix: upstream change")
            git("checkout", "main")
            git("commit", "--allow-empty", "-m", "ci: fork change")
            git("merge", "--no-ff", "upstream", "-m", "Merge branch 'upstream' into main")
            with patch.dict(os.environ, {"GIT_DIR": directory + "/.git"}):
                subjects = conventional_commits.git_subjects(base + "..HEAD")
            self.assertEqual(set(subjects), {"fix: upstream change", "ci: fork change"})
            self.assertTrue(all(map(conventional_commits.valid_subject, subjects)))
            git("commit", "--allow-empty", "-m", "invalid ordinary commit")
            with patch.dict(os.environ, {"GIT_DIR": directory + "/.git"}):
                self.assertIn("invalid ordinary commit", conventional_commits.git_subjects(base + "..HEAD"))
            self.assertFalse(conventional_commits.valid_subject("invalid ordinary commit"))

    def test_subject_validation_does_not_whitelist_merge_text(self):
        self.assertFalse(conventional_commits.valid_subject("Merge untrusted text"))
        self.assertTrue(conventional_commits.valid_subject("ci: check synchronized commits"))
