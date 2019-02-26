#-------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#--------------------------------------------------------------------------

script_dir=$(cd "$(dirname "$0")" && pwd)

export RUNTIMES_TO_INSTALL="2.7.15 3.4.9 3.5.6 3.6.6 3.7.1"

echo "This script will do the following:"
echo "1. Use apt to install pre-requisites for pyenv"
echo "2. Install pyenv"
echo "3. Use pyenv to install the following Python runtimes: ${RUNTIMES_TO_INSTALL}"
echo "4. For each runtime, install virtualenv and create a default environment under your home directory"
echo

read -p "Are you sure you want to do this? [yn] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 0
fi

sudo apt-get install -y make build-essential zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libffi-dev liblzma-dev dos2unix
[ $? -eq 0 ] || { echo "APT failed"; exit 1; }

curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
[ $? -eq 0 ] || { echo "failed installing pyenv"; exit 1; }

cd ${HOME}/.pyenv
[ $? -eq 0 ] || { echo "failed cd ${HOME}/.pyenv"; exit 1; }

# pyenv-installer gives us CRLF when we just want LF.  Force LF
find -type f -a -not \( -path './versions/*' \) -print0 | \
    xargs -0 -I @@ bash -c 'file "$@" | grep ASCII &>/dev/null && dos2unix $@' -- @@

export PATH="${HOME}/.pyenv/bin:${PATH}"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

function build_failure_help {
    echo
    echo "If you're getting an error: ERROR: The Python ssl extension was not compiled. Missing the OpenSSL lib?"
    echo "You MAY need to switch out OpenSSL 1.1.x with OpenSSL 1.0."
    echo "BUT,  doing this will break NPM and other tools that depend on OpenSSL 1.1.x, so BE VERY CAREFUL"
    echo 
    echo "sudo apt install libssl1.0-dev"
    echo
    echo "Or, to learn more, read the following:"
    echo "https://github.com/pyenv/pyenv/wiki/common-build-problems"
    echo "https://github.com/pyenv/pyenv/issues/945"
    echo
    echo "The second link has a comment that suggests a private copy of OpenSSL 1.1.x headers to trick the compiler:"
    echo "https://github.com/pyenv/pyenv/issues/945#issuecomment-409627448"
    echo
}

for RUNTIME in ${RUNTIMES_TO_INSTALL}; do
    echo calling pyenv install -s $RUNTIME
    pyenv install -s $RUNTIME
    [ $? -eq 0 ] || { echo "failed installing Python $RUNTIME"; build_failure_help; exit 1; }

    pyenv shell $RUNTIME
    [ $? -eq 0 ] || { echo "failed calling pyenv to use Python $RUNTIME for this script"; exit 1; }

    python -m pip install --upgrade pip
    [ $? -eq 0 ] || { echo "failed upgrading PIP for Python $RUNTIME"; exit 1; }

    python -m pip install virtualenv
    [ $? -eq 0 ] || { echo "failed installing virtualenv for Python $RUNTIME"; exit 1; }

    python -m virtualenv "${HOME}/env/Python-${RUNTIME}"
    [ $? -eq 0 ] || { echo "failed setting up a virtual environment for Python $RUNTIME"; exit 1; }
done

echo Success!
echo
echo "Use the following commands to switch python versions (or use the aliases below):"
for RUNTIME in $RUNTIMES_TO_INSTALL; do
    echo "source ~/env/Python-${RUNTIME}/bin/activate"
done
echo
echo "Add the following to your .bashrc file:"
echo "export PATH=\"${HOME}/.pyenv/bin:\$PATH\""
echo "eval \"\$(pyenv init -)\""
echo "eval \"\$(pyenv virtualenv-init -)\""
echo "alias pip='python -m pip $@'"
for RUNTIME in $RUNTIMES_TO_INSTALL; do
    echo "alias py-${RUNTIME}='source ~/env/Python-${RUNTIME}/bin/activate'"
done






