Contributing
============

So, you want to contribute? Great!
Contributing is not only about creating fixes, but also reporting bugs.
Before reporting a bug, please make sure to use the latest devel and database revision and recheck the existance of the problem.


Mandatory things when creating a ticket
---------------------------------------

First, visit this link: [Issues of Cutevariant](https://github.com/labsquare/cutevariant/issues).

- Check if your problem/demand is already mentioned in an opened issue (you can bring some additional information here)
- Write a clear title and description of the bug
- Add which version of Cutevariant you're running on by giving us the version from the GUI (Help/About Cutevariant)
or the commit hash you're based on.
- Try to add log file example or at least describe a reproductible way to trigger the bug.
- When reporting a crash, you should run the app in debug mode:

    $ cutevariant -v debug

Note:
- Logs are stored in the temporary directory of the system (/tmp/ on Linux, C:\temp on Windows).
- Some exceptions can be triggered outside the logging process, so console output could be useful.


Creating Pull Requests
----------------------

    # Fork it.
    # Clone the repository
    git clone git@github.com:<your_username>/cutevariant.git
    # Add upstream repo to yours
    git remote add upstream git@github.com:labsquare/cutevariant.git
    # Now your repo is tied to 2 repos: origin (yours), upstream (ours)
    # Sync your git with ours (get the status of existing branches)
    git fetch upstream
    # Create a branch (Note: fixes is an arbitrary name, choose whatever you want here)
    git checkout -b fixes
    # Make & add your changes
    git add --patch
    # Commit your changes (Note: #12345 is the number of the potential issue that presents the problem)
    git commit -am "Added XXX; #12345"
    # Push the branch to your repo
    git push origin fixes
    # Now make a PR from github interface

    # Alternatively, pull our upstream changes
    git checkout devel && git pull upstream


When creating patches, please read:

- [Our Development Standards](https://github.com/labsquare/cutevariant/wiki/Development-standards).


We suggest that you create one branch for each fix:
This will allow you to create more fixes without having to wait for your pull request to be merged.


Wiki
----

The wiki is located at https://github.com/labsquare/cutevariant/wiki.

You will find here a documentation about the structure of the project, development standards, etc.
