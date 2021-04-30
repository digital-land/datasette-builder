import logging

import github
from github import GithubException

logger = logging.getLogger(__name__)


class GithubApi:
    def __init__(self, token, org):
        self.g = github.Github(token)
        self.org = org

    def find_datasets(self):
        output = []
        for repo in self.g.get_organization(self.org).get_repos():
            if not repo.name.endswith("-collection"):
                continue

            if repo.archived:
                logger.info("skipping %s: archived", repo.name)
                continue

            try:
                dataset_dir = repo.get_contents("dataset")
            except GithubException:
                continue

            for file in dataset_dir:
                if file.name.endswith(".sqlite3"):
                    url = file.download_url
                    if file.size < 200:
                        # suspiciously small... probably an LFS pointer
                        if file.decoded_content.decode("utf-8").startswith(
                            "version https://git-lfs"
                        ):

                            url = f"https://media.githubusercontent.com/media/digital-land/{repo.name}/{repo.default_branch}/{file.path}"
                    output.append(
                        {
                            "name": file.name[:-8],
                            "url": url,
                            "repo": repo.name,
                        }
                    )

        return output

    def get_failing_builds(self):
        failures = []
        for repo in self.g.get_organization(self.org).get_repos():
            if repo.name == "github-build-checker":
                continue

            if repo.archived:
                logger.info("skipping %s: archived", repo.name)
                continue

            workflows = repo.get_workflows()
            if workflows.totalCount == 0:
                logger.info("skipping %s: no workflows", repo.name)
                continue

            logger.info(f"{repo.name}: {repo.get_workflows().totalCount} workflows")

            for workflow in workflows:
                if workflow.state != "active":
                    continue

                for run in workflow.get_runs():
                    if run.status != "completed":
                        continue

                    if run.head_branch != repo.default_branch:
                        continue

                    if run.conclusion == "success":
                        break

                    failure = {
                        "repo": repo.name,
                        "workflow": workflow.name,
                        "url": run.html_url,
                    }
                    failures.append(failure)
                    break

        return failures
