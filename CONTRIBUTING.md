# Contributors Guide

This guide summarizes the basic Git workflow for contributing to ElectroSmart.

## Clone the repository

```bash
git clone https://github.com/hansenryang/ElectroSmart.git
cd ElectroSmart
```

To clone into a custom folder:

```bash
git clone https://github.com/hansenryang/ElectroSmart.git your-folder-name
cd your-folder-name
```

## Create a new branch

Do not make changes directly on `main`. Create a new branch before editing files:

```bash
git checkout -b my-custom-branch
```

Check your current branch:

```bash
git branch
```

The branch marked with `*` is your current branch.

## Edit an existing branch

To continue working on an existing branch, switch to it first:

```bash
git checkout my-custom-branch
```

Then pull the latest version of that branch:

```bash
git pull
```

Now you can edit files, commit changes, and push updates to the same branch.

## Switch between branches

To switch to another existing branch:

```bash
git checkout branch-name
```

## Make and commit changes

After editing or adding files, check what changed:

```bash
git status
```

Stage the files you want to commit:

```bash
git add file-name
```

or stage all changes in the current folder:

```bash
git add .
```

Commit the staged changes:

```bash
git commit -m "Describe your change"
```

## Push your branch

Upload your branch to GitHub:

```bash
git push origin my-custom-branch
```

Make sure the branch name is spelled correctly.

## Open a pull request

After pushing your branch, open GitHub and create a pull request from your branch into `main`.

Once the pull request is reviewed and merged, your changes will become part of the main codebase.

## Notes

In the current codebase, `app.py` and `plotting.py` are duplicated in the Windows and MacOS folders. If you modify one copy, make sure to update the other before submitting a pull request.

After your branch is merged, you can delete the local branch:

```bash
git branch -d my-custom-branch
```
