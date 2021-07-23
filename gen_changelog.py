import sys
from typing import List

from git import Repo


def gen_changelog(branch: str = "master") -> None:
    """Создание changelog'а по коммитам."""
    repo = Repo.init()
    assert not repo.bare  # noqa: S101
    messages: List[str] = []
    tagged_commits = [tag.commit for tag in repo.tags]
    for index, commit in enumerate(repo.iter_commits(rev=branch)):
        if index != 0 and commit in tagged_commits:
            break
        messages.append(commit.message.strip())
    with open("CHANGELOG.md", mode="w", encoding="UTF-8") as changelog:
        changelog.write("\n\n".join(messages))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        gen_changelog(sys.argv[1])
    else:
        gen_changelog()
