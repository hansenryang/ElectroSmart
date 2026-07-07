# Contributors Guide

This guide explains how to contribute to the ElectroSmart codebase using Git and GitHub.

## 1. Clone the repository

In your desired folder, clone the repository:

```bash
git clone https://github.com/hansenryang/ElectroSmart.git
```

This will create a folder named `ElectroSmart`.

If you want to clone the repository into a different folder name, use:

```bash
git clone https://github.com/hansenryang/ElectroSmart.git your-folder-name
```

For example:

```bash
git clone https://github.com/hansenryang/ElectroSmart.git "Electrosmart Git"
```

If the folder name contains spaces, use quotation marks when entering the folder:

```bash
cd "Electrosmart Git"
```

## 2. Create a new branch before making changes

When making modifications, always create a branch from the main codebase.

**This is very important:** do not modify code directly on `main`. Changes to `main` affect the code that everyone accesses. Always make sure you are working on a separate branch before editing, committing, or pushing code.

To learn more about branches, see GitHub’s guide:
https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches

To create and switch to a new branch:

```bash
git checkout -b my-custom-branch
```

For example:

```bash
git checkout -b add-contributors-file
```

To confirm which branch you are on:

```bash
git branch
```

You should see something like:

```bash
* my-custom-branch
  main
```

The `*` indicates your current branch.

## 3. Switch between branches

Sometimes you may need to switch from one branch to another, for example if different branches contain different app features or solve different issues.

To switch to another existing branch:

```bash
git checkout new-destination-branch
```

For example:

```bash
git checkout main
```

or:

```bash
git checkout my-custom-branch
```

## 4. Workflow for adding a new file

Use this workflow when the file does not already exist.

For example, to add a new `CONTRIBUTORS.md` file:

```bash
cd "Electrosmart Git"

git checkout my-custom-branch
git pull

touch CONTRIBUTORS.md
```

On Windows PowerShell, use this instead of `touch`:

```powershell
New-Item CONTRIBUTORS.md
```

Then edit the file. After saving your changes:

```bash
git status
git add CONTRIBUTORS.md
git commit -m "Add contributors file"
git push origin my-custom-branch
```

## 5. Workflow for editing an existing file

Use this workflow when the file already exists and you only want to modify it.

```bash
cd "Electrosmart Git"

git checkout my-custom-branch
git pull

# Edit the existing file, then save your changes

git status
git add my_desired_file.py
git commit -m "Update my desired file"
git push origin my-custom-branch
```

For example, if you edited `README.md`:

```bash
git add README.md
git commit -m "Update README"
git push origin my-custom-branch
```

If you want to stage all modified files in the current folder:

```bash
git add .
```

Be careful not to use:

```bash
git add ..
```

because this stages files from the parent folder, which is usually not intended.

## 6. Why stage and commit separately?

A typical workflow is:

```bash
git status
git add .
git commit -m "your custom commit message"
git push origin my-custom-branch
```

Technically, staging and committing can sometimes be combined using:

```bash
git commit -am "your custom commit message"
```

However, it is usually better to keep `git add` and `git commit` separate. This allows you to inspect what Git is staging before committing.

This helps prevent accidentally committing unwanted files, such as:

* local configuration files
* temporary files
* test outputs
* secrets or credentials
* files containing local paths or private information

Always check before committing:

```bash
git status
```

## 7. Push carefully

To push your branch to GitHub:

```bash
git push origin my-custom-branch
```

Make sure to spell the branch name correctly. If the branch name is misspelled, GitHub may unintentionally create a new branch with the wrong name.

## 8. Clean up commit history with rebase

When all relevant changes in a branch are complete, it is good practice to clean up the commit history before making a pull request.

This can be done using `rebase`.

To learn more about rebasing, see GitHub’s guide:
https://docs.github.com/en/get-started/using-git/about-git-rebase

Rebasing can be used to combine multiple small commits into a cleaner commit history. This is useful when several small changes belong to one larger update.

To interactively rebase the last `N` commits:

```bash
git rebase -i HEAD~N
```

Replace `N` with the number of commits you want to review.

For example, to rebase the last 3 commits:

```bash
git rebase -i HEAD~3
```

To rebase from the first commit:

```bash
git rebase -i --root
```

During the interactive rebase, you can choose which commits to keep, edit, squash, or rename.

## 9. Make a pull request

After all changes are finished and pushed to GitHub, find your branch on GitHub and create a pull request.

A pull request allows the code owner or designated reviewers to inspect the changes before they are merged into `main`.

Once the pull request is approved and merged, the changes in your branch become part of the main codebase. These changes will then be used globally when users access the Streamlit app link.

## 10. Important note about duplicate files

In the current version of the codebase, `app.py` and `plotting.py` are stored separately in both the Windows and MacOS folders.

If you modify one of these files, remember to make the corresponding change in the other folder before submitting the final pull request.

This duplicate-code structure may be improved in the future. One possible solution is to use one shared general folder for the main app code, while keeping the Windows and Mac command files separate.

## 11. Delete a branch after it is merged

Once your branch has been merged into `main`, it is good practice to delete the local branch because it is no longer needed.

To delete a local branch:

```bash
git branch -d my-custom-branch
```

If Git does not allow deletion because the branch has not been fully merged, double-check before forcing deletion.

## 12. Forking the app

If contributors do not plan to change the main ElectroSmart codebase, they may instead fork the app or create their own version.

This may be useful if someone wants to add personal features, experiment with new functionality, or maintain a separate version without affecting the main shared app.
