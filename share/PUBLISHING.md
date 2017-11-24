Copyright
=========
Copyright (c) 2017 Wind River Systems, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:
       http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software  distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
OR CONDITIONS OF ANY KIND, either express or implied.


Quick Start
===========

  * Create an account on https://pypi.python.org/pypi

  * Create `.pypirc` and add:
    ```
    [distutils]
    index-servers=
	    pypi
	    testpypi

    [pypi]
    username: USERNAME
    password: PASSWORD

    [testpypi]
    repository = https://test.pypi.org/legacy/
    username = USERNAME
    password = PASSWORD
    ```

  * Configure setup.py
    Note: 'version' cannot contain letters and needs to be updated everytime you upload.

  * Create Packages:
    `python setup.py sdist bdist_wheel`
    `python3 setup.py sdist bdist_wheel`
    **must do both to work with both versions of python

  * Sign package:
    `gpg --detach-sign -a dist/package-name-here.tar.gz`
    **If you have not already set-up a GPG key, create a new keypair. See
    [the GPG handbook](https://www.gnupg.org/gph/en/manual/c14.html)

  * Upload to testing site or main server:
    TEST: `twine upload -r testpypi dist/*`
    MAIN: `twine upload dist/*`

  * Can be installed from testing site or main server:
    TEST: `pip install --extra-index-url https://test.pypi.org/simple/ package-name-here`
    MAIN: `pip install package-name-here`


Publishing
===========
Publishing of the module will be done via Pypi to allow for easy installation
and upgrade via the pip utility. Demo apps will need to be acquired from
elsewhere. There may be DEB and RPM files available as well that will include
the demo apps and library, but this has not been finalized yet.

The instructions below describe how to setup Pypi publishing and how to upload
the module to the repository. They were written for use on Linux-based systems,
and were tested on Ubuntu 16.04 with the following software:
* Python 2.7.12
* twine 1.9.1
* setuptools 36.2.7
* pip 9.0.1

While this guide covers the key things to do when publishing, it does not cover
everything that can be configured/done. For more information, check out these
sites:
* https://packaging.python.org/tutorials/distributing-packages/
* https://pypi.python.org/pypi/twine

## Part 1: First-Time Setup
Before publishing for the first time, an account on
[Pypi](https://pypi.python.org/pypi) is needed. Create an account, then verify
it with the link that will be emailed to you. When you login to your account,
there is an option to add a GPG key. This will be covered later, in section
3a. At the time of writing, it seems that entering a GPG key ID into this field
has no effect on uploading signed packages, thus it can be left blank. Once
this is done, create a new file in your home directory called `.pypirc`. Copy 
the following template into it, replacing the information with your own as
necessary:
```
[distutils]
index-servers=
	pypi
	testpypi

[pypi]
username:yourusername
password:yourpassword

[testpypi]
repository = https://test.pypi.org/legacy/
username = yourusername
password = yourpassword
```
**Note: At the time of writing, many online tutorials were outdated and used
old pypi endpoints due to the migration of the site. 
For more information, [see this post](https://mail.python.org/pipermail/distutils-sig/2017-June/030766.html)**

Notice how there are two different servers: pypi and testpypi. testpypi can be
used to test your configuration prior to publishing on the main pypi repository.
This site does require a separate account from the main pypi site.

If you don't currently have pip installed, install it from your system's
package manager, eg. `sudo apt install python-pip`. Once it is installed,
run `pip install --upgrade pip` to upgrade to the absolute latest version.

Next, use pip to install the required Python distribution modules:
`pip install twine setuptools`

## Part 2: Package Configuration
To publish to Pypi, the module must first be configured via `setup.py`. In that
file there are various parameters inside the `setup` function call that
describe the package and how it should be installed. Each time the package is
published, the version must be updated and other parameters should be updated
as necessary. *Note: `version` cannot contain letters. The online documentation
and some error messages state that they are supported, but every attempt to
upload a package with letters in the version has failed.*

For a full list of parameters, see the.
[Python Documentation](https://packaging.python.org/tutorials/distributing-packages/#setup-args).
Most parameters present in `setup.py` should be self-explanatory and accept
most input. The `classifiers` field is a bit different and uses a certain set
of entries. They are mostly used to categorize (classify) the package to make
it easier to find. In our `setup.py`, the operating systems that are specified
are the ones that the module was tested on, not the list of systems that it
will likely support (for example, it is expected that the module will work on
Windows 10, however this was not officially tested at the time of writing, and
thus it is/was not present in the classifiers).

For a full list of valid entries for the `classifiers` field,
[see this list](https://pypi.python.org/pypi?%3Aaction=list_classifiers).

## Part 3: Packaging
Next, the module must be packaged. Two different packages will be
generated: a binary Python "wheel" package and a source package. The wheel
package will allow for quick installation without the need for compilation of
the module, whereas the source package will require compilation but allows the
end user to make their own changes to the library. Generation of these packages
is done by running the following command from the root of the repo:
`python setup.py sdist bdist_wheel`. Two new tar.gz files will be created in a
new subdirectory called `dist`.

### Part 3a: Signing
It is highly recommended that all packages that are uploaded are
[GPG/PGP](https://en.wikipedia.org/wiki/GNU_Privacy_Guard) signed.
If you have not already set-up a GPG key, see
[the GPG handbook](https://www.gnupg.org/gph/en/manual/c14.html) for how to
create a new keypair. Once you have done this and exported your packages, run
the following GPG command:
`gpg --detach-sign -a dist/package-name-here.tar.gz`, using the correct name for
your package. If you get an error about not having a default key, or if you
would like to use a specific key, the `-u <ID>` flag allows you to specify the 
key to use to sign the package. You will need to do this twice: once for the 
binary distribution and once for the source distribution.

## Part 4: Uploading
If you want to test your upload first on the testpypi server, use the following command:
`twine upload -r testpypi dist/*`. A list of files separated by spaces can be
substituted for `dist/*` if you do not want to upload all the files in `dist`,
for example if you have other (non-package related) files there. If you choose
to specify a list of files, make sure to include the .asc file for each package
if you signed them.

When you're satisfied with your packages, run `twine upload dist/*` to upload
to the main server.

## Part 5: Installing via pip
Once you have completed Part 4, the module can be downloaded directly from the
pip utility. Simply run `pip install <package>` as you would with any other
package, or `pip install --upgrade <package>` if you have an existing install.
