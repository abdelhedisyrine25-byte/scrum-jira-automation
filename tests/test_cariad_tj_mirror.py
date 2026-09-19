import os
import unittest
from unittest.mock import Mock, patch

import cariad_tj_mirror


class JiraTests(unittest.TestCase):
    def make_client(self, prefix="TEST", **values):
        environment = {
            f"{prefix}_URL": "https://jira.example",
            f"{prefix}_TOKEN": "token",
            **values,
        }
        with patch.dict(os.environ, environment, clear=False):
            return cariad_tj_mirror.Jira(prefix)

    def test_read_only_post_is_rejected_before_http(self):
        with patch.dict(os.environ, {"CARIAD_URL": "https://jira.example", "CARIAD_TOKEN": "token"}, clear=False):
            client = cariad_tj_mirror.Jira("CARIAD", read_only=True)

        client.s.post = Mock()
        with self.assertRaisesRegex(RuntimeError, "read-only Jira client"):
            client.post("/rest/api/2/issue", {})

        client.s.post.assert_not_called()

    def test_data_center_search_paginates_until_total(self):
        client = self.make_client()
        client.cloud = False
        client.get = Mock(side_effect=[
            {"issues": [{"key": "TJ-1"}], "total": 2},
            {"issues": [{"key": "TJ-2"}], "total": 2},
        ])

        result = client.search("project = TJ", ["summary"])

        self.assertEqual(["TJ-1", "TJ-2"], [issue["key"] for issue in result])
        self.assertEqual(2, client.get.call_count)
        self.assertEqual(0, client.get.call_args_list[0].args[1]["startAt"])
        self.assertEqual(1, client.get.call_args_list[1].args[1]["startAt"])

    def test_cloud_search_uses_next_page_token(self):
        client = self.make_client()
        client.cloud = True
        client.get = Mock(side_effect=[
            {"issues": [{"key": "TJ-1"}], "nextPageToken": "next", "isLast": False},
            {"issues": [{"key": "TJ-2"}], "isLast": True},
        ])

        result = client.search("project = TJ", ["summary"])

        self.assertEqual(["TJ-1", "TJ-2"], [issue["key"] for issue in result])
        self.assertNotIn("nextPageToken", client.get.call_args_list[0].args[1])
        self.assertEqual("next", client.get.call_args_list[1].args[1]["nextPageToken"])


class MoveTests(unittest.TestCase):
    def test_dry_run_does_not_post_transition(self):
        client = Mock()
        client.get.return_value = {"transitions": [{"id": "7", "to": {"name": "Execution"}}]}

        cariad_tj_mirror.move(client, "INT-1", "Execution", apply=False)

        client.get.assert_called_once_with("/rest/api/2/issue/INT-1/transitions")
        client.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
