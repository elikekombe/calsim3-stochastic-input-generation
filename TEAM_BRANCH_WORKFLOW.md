# Team GitHub Workflow

Use this workflow to work together in the shared fork. `main_jacobs` is the team integration branch; each person does their work on a separate feature branch.

## 1. Start a feature branch

Because you have been added as a collaborator to the shared fork, you can create your own branch there. If you already have the project cloned, update your local `main_jacobs` branch first:

```bash
git switch main_jacobs
git pull origin main_jacobs
git switch -c <your-name>/<short-task-name>
```

If you do not have a local clone yet, clone the shared fork using its GitHub URL, then run the commands above. In GitHub, you can also select `main_jacobs` in the branch menu and choose **Create branch**. Example branch name: `eli/fix-leap-day-wind`. Create each feature branch from the latest `main_jacobs`, not from another person's feature branch.

## 2. Make and save your changes

Work only on your feature branch. Before committing, review the files you changed. Make small, focused commits with clear messages:

```bash
git status
git add <files-to-include>
git commit -m "Describe the change"
```

Do not commit data files, generated outputs, credentials, or local machine settings unless the team specifically agreed they belong in Git.

## 3. Keep your branch up to date

Before opening your pull request, bring in the latest team changes:

```bash
git fetch origin
git merge origin/main_jacobs
```

If Git reports conflicts, resolve them, review the result, then commit the merge. Ask the team for help if you are unsure which version to keep.

## 4. Push and open a pull request

Push your branch to the shared fork:

```bash
git push -u origin <your-name>/<short-task-name>
```

On GitHub, create a pull request with:

- **Base repository:** the shared fork
- **Base branch:** `main_jacobs`
- **Compare branch:** your feature branch

Describe what changed, why, and how you checked it. Request a teammate review. Merge only after review and any agreed checks are complete. Do not push directly to `main_jacobs`.

## 5. Start the next task

After your pull request is merged, update the integration branch and create a fresh feature branch:

```bash
git switch main_jacobs
git pull origin main_jacobs
git switch -c <your-name>/<next-task-name>
```

When the team is ready to submit its combined work, the project lead can open a separate pull request from the shared fork's `main_jacobs` branch to the external team's repository. Confirm the target branch with that team first.
