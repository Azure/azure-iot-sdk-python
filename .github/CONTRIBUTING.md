# The Azure IoT SDKs team wants to hear from you

- [Need Support?](#need-support)
- [File a bug (code or documentation)](#file-a-bug-code-or-documentation)
- [Contribute code and/or documentation](#contribute-code-andor-documentation)
- [Commit messages](#commit-messages)
- [Editing module requirements](#editing-module-requirements)
- [Adding new files](#adding-new-files)

## Need Support

- **Have a feature request for SDKs?** Please post it on [User Voice](https://feedback.azure.com/forums/321918-azure-iot) to help us prioritize
- **Have a technical question?** Ask on [Stack Overflow with tag "azure-iot-hub"](https://stackoverflow.com/questions/tagged/azure-iot-hub)
- **Need Support?** Every customer with an active Azure subscription has access to [support](https://docs.microsoft.com/en-us/azure/azure-supportability/how-to-create-azure-support-request) with guaranteed response time.  Consider submitting a ticket and get assistance from Microsoft support team
- **Found a bug?** Please help us fix it by thoroughly documenting it and filing an issue on GitHub (See below).

## File a bug (code or documentation)

That is definitely something we want to hear about. Please open an issue on github, we'll address it as fast as possible. Typically here's the information we're going to ask for to get started:

- What version of the SDK are you using?
- Do you have a snippet of code that would help us reproduce the bug?
- Do you have logs showing what's happening?

Our SDK is entirely open-source and we do accept pull-requests if you feel like taking a stab at fixing the bug and maybe adding your name to our commit history :) Please mention
any relevant issue number in the pull request description.

## Contribute code and/or documentation

We look at all pull requests submitted against the `master` branch carefully. We also actively use the [Wiki](https://github.com/Azure/azure-iot-sdk-node/wiki) for longer-form documents. The wiki can be cloned and used as a regular Git repository so feel free to contribute there too!

As far as code is concerned the code associated with the PR will be pulled and run through the gated build before it makes it to the master branch. As much as possible, we insist on having tests associated with the code, and if necessary, additions/modifications to the requirement documents. As a matter of fact, the build will fail if code coverage goes down.

Also, have you signed the [Contribution License Agreement](https://cla.microsoft.com/) ([CLA](https://cla.microsoft.com/))? A friendly bot will remind you about it when you submit your pull-request.

If you feel like your contribution is going to be a major effort, you should probably give us a heads-up. We have a lot of items captured in our backlog and we release every two weeks, so before you spend the time, just check with us to make
sure your plans and ours are in sync :) Just open an issue on github and tag it "enhancement" or "feature request"

### Commit messages

This project follows the [Conventional Commits convention](https://www.conventionalcommits.org), meaning that your commits message should be structured as follows:

```Shell
<type>[optional scope]: <description>
[optional body]
[optional footer]
```

The commit should contains one of the following structural elements as the \<type\>:

- `fix:` a commit of the type fix patches a bug in your codebase (this correlates with PATCH in semantic versioning).
- `feat:` a commit of the type feat introduces a new feature to the codebase (this correlates with MINOR in semantic versioning).
- Others: commit types other than `fix:` and `feat:` are allowed such as `chore:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, and others. Refer to [@commitlint/config-conventional](https://github.com/conventional-changelog/commitlint/tree/master/%40commitlint/config-conventional) for a full list.

If you are new to this convention you can use `npm run commit` instead of `git commit` and follow the guided instructions.

## Editing module requirements

We use requirement documents to describe the expected behavior for each code modules. It works as a basis to understand what tests need to be written.

When contributing to markdown requirement docs (located in the `devdoc` folder alongside the code, you should use `99` for a developer id, and just increment the last number of the requirement to be unique.

## Adding new files

If your contribution is not part of an already existed code, you must create a new requirement file and a new set of unit tests project in the appropriate `devdoc`  and `test` directories.
