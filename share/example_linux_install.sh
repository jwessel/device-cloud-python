#!/bin/sh

# ----------------------------------------------------------------------
# This is an example script to show how to install the
# device-cloud-repo on a typical Linux system.  This script does a pip
# install  to make sure all dependencies are satisfied.  This script
# sets up a config dir in /etc/python-device-cloud and a runtime dir
# in /var/lib/python-device-cloud.  All other examples and docs are
# installed into /usr/share/python-device-cloud.  A service file is
# installed to monitor the service (systemd)
#
# Requirements:
#  * run as root
#  * run from the top level directory,
#   e.g. sudo ./share/example_linux_install.sh
# ----------------------------------------------------------------------

root_dir="/"
pkg_name=python-device-cloud
etc_dir=${root_dir}etc/${pkg_name}
var_dir=${root_dir}var/lib/python-device-cloud
bin_dir=${root_dir}usr/local/bin
share_dir=${root_dir}usr/share/${pkg_name}
service_dir=${root_dir}lib/systemd/system

# decide who to run the service as, defaults to root
dc_user=root
dc_group=root

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo "Install locations:"
echo "    $etc_dir"
echo "    $var_dir"
echo "    $bin_dir"
echo "    $share_dir"
echo "    $service_dir"

echo "Default user|group: ${dc_user}:${dc_group}"
echo "Installing $pkg_name and dependencies"

# install the python modules globally
pip install .

mkdir -p $etc_dir
mkdir -p $var_dir
mkdir -p $bin_dir
mkdir -p $share_dir
mkdir -p $service_dir

chown ${dc_user}:${dc_group} $etc_dir
chown ${dc_user}:${dc_group} $var_dir

# process other .in files
cat share/device-manager.service.in | sed -e "s|%user%|${dc_user}|" \
	-e "s|ExecStart=/usr/bin|ExecStart=$bin_dir|" \
	-e "s|^#WorkingDirectory.*|WorkingDirectory=${var_dir}|" \
	 > "${service_dir}/device-manager.service"

cat share/cloud-test.py.in | sed -e "s|%bindir%|${bin_dir}|" \
	-e "s|%vardir%|${var_dir}|" -e "s|%etcdir%|${etc_dir}|" > "${share_dir}/cloud-test.py"

# install executable scripts
install -m 755 device_manager.py ${bin_dir}/device_manager.py

# update some configuration locations
sed -i "s|default_cfg_dir = \".\"|default_cfg_dir = \"${etc_dir}\"|" ${bin_dir}/device_manager.py
sed -i "s|systemd_controlled = False|systemd_controlled = True|" ${bin_dir}/device_manager.py

# update the runtime dir in iot.cfg
install -m 644 iot.cfg ${etc_dir}/iot.cfg
sed -i "s|:\"runtime\"|:\"${var_dir}\"|" ${B}/iot.cfg

systemctl enable  device-manager.service

echo
echo "+------------------------------------------------------------------------------"
echo "System installed."
echo "Next Steps:"
echo "    * configure for cloud connection using generate_script.py."
echo "    * start the service: systemctl start device-manager"
echo "    * tail the log for details: journalctl -f -u device-manager"
echo "+------------------------------------------------------------------------------"
