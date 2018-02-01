Contributing To The device-cloud-python Project
===============================================
Firstly, thanks for your interest in advancing the project!  All bug fixes and features are handled via pull request in github.  The project can be forked, but in order to be considered, you need to have your changes validated on the main repo.  Our CI runs on the main repo only.  This will require branch write access. Only the administrators have write access to the master branch, but contributors can push their changes to topic branches.

Obtaining Branch Write Privilege
--------------------------------
Send an email with subject line:
  "Request branch write access to device-cloud-python"
to the maintainer (paulbarrette@gmail.com) for branch write access.
Include your github ID.  The maintainers will add you.

Process
-------
Once you have branch write access, do the following and work with the
maintainers to get your changes accepted:

  * Clone the repo and checkout the master branch (default).
  * Follow the coding format in the file you are changing.
  * Follow the commit log standard, and write a reasonable commit log. (See below).
  * Sign off your commits.
  * Create a topic branch and push it to origin.
    * $ git branch foo
    * $ git checkout foo
    * make changes and commit
    * run the unit tests! They must pass.  CI runs them as well. (e.g. $ pytest)
    * $ git push origin foo:foo
    * There is one topic branch per pull request.
  * Create a pull request and select your branch (e.g. foo)
    Once the pull request is created, CI will run on it and sanitize the
    code.  Before the reviewers start the review, CI must pass.
  * Reviewers may accept your changes or request further change.  If you
    need to make further changes, push them to the same topic branch.
  * All licensing must comply with Apache-2.0.
  * Merge commits are not allowed

Commit Log Format
-----------------
The commit format is:

  * Short log with file(s) affect (80 chars)
  * Second line must be blank
  * Third line may be the bug fix reference
  * Next, the long log follows.  Explain what the commit addresses,
    add an error log snippet if possible
  * Finally, add your sign off

Here is an example commit log:

```
commit 865f08c8a67a2a1eb663ba725fbc348071aa3d2c
Author: Paul Barrette <paulbarrette@gmail.com>
Date:   Thu Feb 1 14:52:45 2018 -0500

    handler.py: add some missing exception catches.
    
    Resolves #179
    Make sure to catch exceptions when running the iot-simpe-telemetry
    application, which now reads back the current sample.
    
    Signed-off-by: Paul Barrette <paulbarrette@gmail.com>
```

Have a look at the commit history to see more examples.

Unit Tests
----------
Unit tests are available using pytest.  Run the following:

```
# python 2.7.9+
pytest

# python 3.4.+
python3 -m pytest
```

Search for bugs
---------------
This project uses [Github](https://github.com/Wind-River/device-cloud-python/issues) for development and issues.
Check for existing bugs before [Opening A New Bug](https://github.com/Wind-River/device-cloud-python/issues/new)
