# Contributing workflow

## Branching

- `main` is always working and always deployable. Nothing is committed
  here directly, it's protected in GitHub settings.
- Every feature gets its own branch off `main`:
  `feature/<short-name>`, e.g. `feature/direct-dfa`, `feature/ll1-table`.
- Small fixes: `fix/<short-name>`.

## Workflow for one feature

1. `git checkout main && git pull`
2. `git checkout -b feature/<short-name>`
3. Build and commit in small, working chunks, don't wait until the whole
   feature is done to make the first commit.
4. `git push -u origin feature/<short-name>`
5. Open a pull request into `main` on GitHub.
6. Wait for the CI check (pytest) to pass.
7. Merge using **squash and merge** so `main`'s history stays one clean
   commit per feature.
8. Delete the branch after merging.
9. If this milestone is a tagged release, tag it on `main`:
   `git tag v0.x && git push origin v0.x`

## Commit message style

- `feat: add followpos DFA construction`
- `fix: handle empty regex in parser`
- `test: add cases for LL(1) conflict detection`
- `docs: update roadmap after milestone 3`

## Before opening a pull request

- Run `pytest -v` locally in `backend/` and make sure everything passes.
- Update `docs/ROADMAP.md`, checking off the milestone you just finished.
- Keep the PR scoped to one milestone. If you find yourself touching
  unrelated files, that's a sign it should be a separate branch.
