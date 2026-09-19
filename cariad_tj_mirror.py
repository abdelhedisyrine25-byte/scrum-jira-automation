#!/usr/bin/env python3
"""Mirror CARIAD Jira TestJobs into the internal Jira, one ticket per TestJob.

CARIAD side: read-only. Only GET requests are possible (enforced in the client).
Internal side: creates missing tickets and moves them to the mapped status.
Dry run by default. Pass --apply to change the internal Jira.

Environment variables (keep them in CI secrets, never in the code):
  CARIAD_URL, CARIAD_TOKEN, [CARIAD_USER], [CARIAD_CLOUD=1]
  INT_URL,    INT_TOKEN,    [INT_USER],    [INT_CLOUD=1]
  CARIAD_JQL    filter for your team's TestJobs, e.g.
                project = XYZ AND issuetype = TestJob AND status in (...)
  INT_PROJECT   internal project key
  INT_ISSUETYPE internal issue type name (default: Task)

Auth: with *_USER set, basic auth (Cloud: email + API token).
Without *_USER, bearer token (Data Center personal access token).
"""
import argparse
import logging
import os
import sys

import requests

log = logging.getLogger("tj-mirror")

# CARIAD status -> internal status. Edit to match your workflows.
STATUS_MAP = {
    "ECU Preparation": "ECU Preparation",
    "ECU Ready": "ECU Ready",
    "Execution": "Execution",
    "Blocked": "Blocked",
    "Waiting for Analysis": "Waiting for Analysis",
    "Analysis": "Analysis",
    "Defect Discussion": "Defect Discussion",
    "Documentation": "Documentation",
}


class Jira:
    def __init__(self, prefix, read_only=False):
        self.url = os.environ[f"{prefix}_URL"].rstrip("/")
        self.cloud = os.environ.get(f"{prefix}_CLOUD", "0") == "1"
        self.read_only = read_only
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/json"
        user = os.environ.get(f"{prefix}_USER")
        token = os.environ[f"{prefix}_TOKEN"]
        if user:
            self.s.auth = (user, token)
        else:
            self.s.headers["Authorization"] = f"Bearer {token}"

    def get(self, path, params=None):
        r = self.s.get(self.url + path, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def post(self, path, body):
        if self.read_only:
            raise RuntimeError("write attempted on a read-only Jira client")
        r = self.s.post(self.url + path, json=body, timeout=30)
        r.raise_for_status()
        return r.json() if r.content else {}

    def search(self, jql, fields):
        """All issues matching jql, using GET only."""
        issues = []
        if self.cloud:
            page_token = None
            while True:
                params = {"jql": jql, "fields": ",".join(fields), "maxResults": 100}
                if page_token:
                    params["nextPageToken"] = page_token
                data = self.get("/rest/api/2/search/jql", params)
                issues += data.get("issues", [])
                page_token = data.get("nextPageToken")
                if data.get("isLast", True) or not page_token:
                    return issues
        start = 0
        while True:
            params = {"jql": jql, "fields": ",".join(fields), "startAt": start, "maxResults": 100}
            data = self.get("/rest/api/2/search", params)
            issues += data["issues"]
            start += len(data["issues"])
            if not data["issues"] or start >= data["total"]:
                return issues


def move(dst, issue_key, target, apply):
    transitions = dst.get(f"/rest/api/2/issue/{issue_key}/transitions")["transitions"]
    match = [t for t in transitions if t["to"]["name"] == target]
    if not match:
        log.warning("%s: no transition available to '%s' (check the internal workflow)", issue_key, target)
        return
    log.info("%s: move to '%s'", issue_key, target)
    if apply:
        dst.post(f"/rest/api/2/issue/{issue_key}/transitions", {"transition": {"id": match[0]["id"]}})


def main(apply):
    src = Jira("CARIAD", read_only=True)
    dst = Jira("INT")
    project = os.environ["INT_PROJECT"]
    issuetype = os.environ.get("INT_ISSUETYPE", "Task")

    testjobs = src.search(os.environ["CARIAD_JQL"], ["summary", "status"])
    log.info("%d TestJobs returned by the CARIAD filter", len(testjobs))

    for tj in testjobs:
        key = tj["key"]
        summary = tj["fields"]["summary"]
        status = tj["fields"]["status"]["name"]
        target = STATUS_MAP.get(status)
        if not target:
            log.warning("%s: CARIAD status '%s' has no mapping, skipped", key, status)
            continue

        label = f"cariad-{key}"
        found = dst.search(f'project = "{project}" AND labels = "{label}"', ["status"])

        if found:
            issue_key = found[0]["key"]
            current = found[0]["fields"]["status"]["name"]
        else:
            log.info("%s: create internal ticket", key)
            if not apply:
                continue
            created = dst.post("/rest/api/2/issue", {"fields": {
                "project": {"key": project},
                "issuetype": {"name": issuetype},
                "summary": f"{key} | {summary}",
                "labels": [label],
            }})
            issue_key = created["key"]
            current = dst.get(f"/rest/api/2/issue/{issue_key}", {"fields": "status"})["fields"]["status"]["name"]

        if current != target:
            move(dst, issue_key, target, apply)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write to the internal Jira (default: dry run)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not args.apply:
        log.info("Dry run: nothing will be written")
    sys.exit(main(args.apply))
