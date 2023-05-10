# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

script_dir=$(cd "$(dirname "$0")" && pwd)

echo "Checking for moby install"
unset moby_cli_installed
dpkg -s moby-cli | grep -q "install ok installed"
if [ $? -eq 0 ]; then moby_cli_installed=true; fi

unset moby_engine_installed
dpkg -s moby-engine | grep -q "install ok installed"
if [ $? -eq 0 ]; then moby_engine_installed=true; fi

need_moby=true
if [ $moby_engine_installed ] && [ $moby_cli_installed ]; then
  echo "moby is already installed"
  unset need_moby
fi

if [ "$need_moby" ]; then
  echo "checking for docker install"
  which docker > /dev/null
  if [ $? -eq 0 ]; then
    echo "docker is already installed"
    unset need_moby
  fi
fi

if [ "$need_moby" ]; then
  $script_dir/install-microsoft-apt-repo.sh
  [ $? -eq 0 ] || { echo "install-microsoft-apt-repo failed"; exit 1; }

  echo "installing moby"
  sudo apt-get install -y moby-engine
  [ $? -eq 0 ] || { echo "apt-get failed"; exit 1; }

  sudo apt-get install -y moby-cli
  [ $? -eq 0 ] || { echo "apt-get failed"; exit 1; }

  # wait for the docker engine to start.
  sleep 10s
fi

# add a group called 'docker' so we can add ourselves to it.  Sometimes it gets automatically created, sometimes not.
echo "creating docker group"
sudo groupadd docker
# allowed to fail if the group already exists

# add ourselves to the docker group.  The user will have to restart the bash prompt to run docker, so we'll just
# sudo all of our docker calls in this script.
echo "adding $USER to docker group"
sudo usermod -aG docker $USER
[ $? -eq 0 ] || { echo "usermod failed"; exit 1; }

echo "Moby/Docker successfully installed"

