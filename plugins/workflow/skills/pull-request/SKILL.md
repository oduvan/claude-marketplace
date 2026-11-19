---
name: pull-request
description: The owner's conventions for branches, pull request titles, pull request descriptions and merging on GitHub. Use before creating a branch for a change, before opening a pull request, when writing or updating a pull request title or description, and when asked to merge one.
---

# Pull request

Follow these steps whenever a change is going to a pull request. They are the
owner's conventions, taken from the history of their repositories.

## 1. Branch

- One new branch per pull request, cut from the default branch.
- Name it as a short description of the change: two to four lower-case words
  joined by dashes, for example `drop-x-draft`, `sequence-stop`,
  `reads-through-sql`. No prefix, no type word, no issue number.
- Never reuse a branch whose pull request is already merged, and do not open
  a second pull request from the same branch.
- When the session starts on a generated branch name, such as
  `claude/wizardly-johnson-foi2fs`, create a properly named branch for the
  work and leave the generated branch alone. Cut the new branch from the
  default branch when the generated one has no commits of its own
  (uncommitted changes come along with `git switch -c <name>`), and from the
  generated branch when it already holds the work. If the session is bound
  to its branch and cannot push another, keep the branch and say so in the
  reply.

## 2. Title

The title becomes the commit on the default branch, so it must make sense
alone in the log.

- Say what is true after the merge, in the owner's words:
  `Deploy: build the image on the runner, never on the server`,
  `Expired calls need a new draft before approval`.
- When the repository has clear areas, start with the area and a colon:
  `CI:`, `Deploy:`, `API calls:`, `Docs sync:`.
- For a versioned plugin or package, start with its name and new version:
  `lyabah-docs 0.9.0: the sequence_stop parameter mark`.
- One line, sentence case, no full stop at the end.
- No type words (`feat:`, `fix:`, `chore:`) and no issue number.

## 3. Description

Write it in plain, simple English with short sentences, for the owner who
will read it on a phone. Save it to a file and pass the file to `gh`.

- **Open with what changes**, in one short paragraph with no heading, from the
  point of view of the person who uses the thing. When it helps, say how it
  was before and how it is now.
- **`## Why`** when the change answers a problem: what happened and what
  caused it, with the numbers or the error if there are any.
- **Sections named after what the reader gets**, with bullets, when the
  change has more than one part. For example `## What the owner gets on the
  group page`, `## How a call is sent`.
- **`## How it was checked`**, always: the commands or tests that were run
  and what came out. If nothing was run, say that in one line.
- **What merging does**, when merging has an effect of its own: a deploy
  runs, a migration applies, another repository must be merged first.
- **Related work** in other repositories as `owner/repo#number`, for example
  "This goes with oduvan/lyabah-service#27."

Never put a list of the changed files in the description.

Leave the "Generated with Claude Code" footer that the session adds at the
end.

## 4. Open it

```bash
git push -u origin <branch>
gh pr create --base <default-branch> --head <branch> --title "<title>" --body-file <file>
```

In a Claude Code cloud session `gh pr create` fails with "GraphQL is not
available". Use the REST call there:

```bash
gh api repos/<owner>/<repo>/pulls -X POST \
  -f title="<title>" -f head="<branch>" -f base="<default-branch>" -F body=@<file>
```

## 5. Merge

Merge only when the owner asks for it.

- Squash. The commit title is the pull request title followed by its number:
  `Drop the X-Draft response header (#26)`.
- Delete the branch after the merge.

```bash
gh pr merge <number> --squash --delete-branch --subject "<title> (#<number>)"
```

In a Claude Code cloud session:

```bash
gh api repos/<owner>/<repo>/pulls/<number>/merge -X PUT \
  -f merge_method=squash -f commit_title="<title> (#<number>)"
gh api repos/<owner>/<repo>/git/refs/heads/<branch> -X DELETE
```
