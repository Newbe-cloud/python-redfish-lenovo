###
#
# Lenovo Redfish examples - Update FW
#
# Copyright Notice:
#
# Copyright 2018 Lenovo Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
###


import sys
import redfish
import json
import time
import lenovo_utils as utils


def update_fw(ip, login_account, login_password, image, targets, fsprotocol, fsport, fsip, fsusername, fspassword, fsdir):
    """Update firmware
    :params ip: BMC IP address
    :type ip: string
    :params login_account: BMC user name
    :type login_account: string
    :params login_password: BMC user password
    :type login_password: string
    :params image_url: User firmware driver url
    :type image_url: string
    :params targets: Targets list
    :type targets: list
    :params protocol: User update transfer Protocol
    :type protocol: string
    :returns: returns update firmware result when succeeded or error message when failed
    """
    # Connect using the address, account name, and password
    login_host = "https://" + ip 
    try:
        # Create a REDFISH object
        result = {}
        REDFISH_OBJ = redfish.redfish_client(base_url=login_host, username=login_account,
                                         password=login_password, default_prefix='/redfish/v1')
        REDFISH_OBJ.login(auth="session")
    except:
        result = {'ret': False, 'msg': "Please check the username, password, IP is correct"}
        return result

    try:
        # Get ServiceRoot resource
        response_base_url = REDFISH_OBJ.get('/redfish/v1', None)
        # Get response_update_service_url
        if response_base_url.status == 200:
            update_service_url = response_base_url.dict['UpdateService']['@odata.id']
        else:
            message = utils.get_extended_error(response_base_url)
            result = {'ret': False, 'msg': "Url '%s' response Error code %s, \nError message :%s" % ('/redfish/v1', response_base_url.status, message)}
            return result

        response_update_service_url = REDFISH_OBJ.get(update_service_url, None)
        if response_update_service_url.status == 200:
            firmware_inventory_url = response_update_service_url.dict['Actions']['#UpdateService.SimpleUpdate']['target']
            image_url = fsprotocol.lower() + "://" + fsusername + ":" + fspassword + "@" + fsip + "/" + fsdir + "/" + image
            parameter = {"ImageURI": image_url, "Targets": targets, "TransferProtocol": fsprotocol.upper()}
            response_firmware_inventory = REDFISH_OBJ.post(firmware_inventory_url, body=parameter)
            if response_firmware_inventory.status in [200, 204]:
                result = {'ret': True, 'msg': "Update firmware successfully"}
                return result
            elif response_firmware_inventory.status == 202:
                task_uri = response_firmware_inventory.dict['@odata.id']
                result = task_monitor(REDFISH_OBJ, task_uri)
                # Delete task
                REDFISH_OBJ.delete(task_uri, None)
                if result["ret"] is True:
                    task_state = result["msg"]
                    if task_state == "Completed":
                        result = {'ret': True, 'msg': "Update firmware successfully"}
                    else:
                        result = {'ret': False, 'msg': "Update firmware failed, task state is %s"  %task_state}
                else:
                    return result
            else:
                message = utils.get_extended_error(response_firmware_inventory)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s, \nError message :%s" % (
                firmware_inventory_url, response_firmware_inventory.status, message)}
                return result
        else:
            message = utils.get_extended_error(response_update_service_url)
            result = {'ret': False, 'msg': "Url '%s' response Error code %s, \nError message :%s" % (update_service_url, response_update_service_url.status, message)}
            return result
    except Exception as e:
        result = {'ret': False, 'msg': "error_message: %s" % (e)}
    finally:
        # Logout of the current session
        REDFISH_OBJ.logout()
        return result


def flush():
    list = ['|', '\\', '-', '/']
    for i in list:
        sys.stdout.write(' ' * 100 + '\r')
        sys.stdout.flush()
        sys.stdout.write(i + '\r')
        sys.stdout.flush()
        time.sleep(0.1)


def task_monitor(REDFISH_OBJ, task_uri):
    """Monitor task status"""
    RUNNING_TASK_STATE = ["New", "Pending", "Service", "Starting", "Stopping", "Running", "Cancelling", "Verifying"]
    END_TASK_STATE = ["Cancelled", "Completed", "Exception", "Interrupted", "Suspended"]
    current_state = ""
    while True:
        response_task_uri = REDFISH_OBJ.get(task_uri, None)
        if response_task_uri.status == 200:
            task_state = response_task_uri.dict["TaskState"]
            if task_state in RUNNING_TASK_STATE:
                if task_state != current_state:
                    current_state = task_state
                    print('Task state is %s, waite a minute' % current_state)
                    continue
                else:
                    flush()
            elif task_state.startswith("Downloading"):
                sys.stdout.write(' ' * 100 + '\r')
                sys.stdout.flush()
                sys.stdout.write(task_state + '\r')
                sys.stdout.flush()
                continue
            elif task_state.startswith("Update"):
                sys.stdout.write(' ' * 100 + '\r')
                sys.stdout.flush()
                sys.stdout.write(task_state + '\r')
                sys.stdout.flush()
                continue
            elif task_state in END_TASK_STATE:
                print("End of the task")
                result = {'ret':True, 'msg': task_state}
                return result
            else:
                result = {"ret":False, "msg":"Task Not conforming to Schema Specification"}
                return result
        else:
            message = utils.get_extended_error(response_task_uri)
            result = {'ret': False, 'msg': "Url '%s' response Error code %s, \nError message :%s" % (task_uri, response_task_uri.status, message)}
            return result


import argparse
def add_helpmessage(argget):
    argget.add_argument('--image', type=str, required=True, help='Specify the fixid of the firmware to be updated.')
    argget.add_argument('--targets', nargs='*', required=True, help='Input the targets list')
    argget.add_argument('--fsprotocol', type=str, help='Specify the file server protocol.Support:["SFTP"]')
    argget.add_argument('--fsport', type=int, default='22', help='Specify the file server port')
    argget.add_argument('--fsip', type=str, help='Specify the file server ip.')
    argget.add_argument('--fsusername', type=str, help='Specify the file server username.')
    argget.add_argument('--fspassword', type=str, help='Specify the file server password.')
    argget.add_argument('--fsdir', type=str, help='Specify the file server dir to the firmware upload.')

import os
import configparser
def add_parameter():
    """Add update firmware parameter"""
    argget = utils.create_common_parameter_list()
    add_helpmessage(argget)
    args = argget.parse_args()

    # Get the configuration file name if the user specified
    config_file = args.config

    # Get the common parameter from the configuration files
    config_ini_info = utils.read_config(config_file)

    # Add FileServerCfg parameter to config_ini_info
    cfg = configparser.ConfigParser()
    if os.path.exists(config_file):
        cfg.read(config_file)
        config_ini_info["fsprotocol"] = cfg.get('FileServerCfg', 'FSprotocol')
        config_ini_info["fsport"] = cfg.get('FileServerCfg', 'FSport')
        config_ini_info["fsip"] = cfg.get('FileServerCfg', 'FSip')
        config_ini_info["fsusername"] = cfg.get('FileServerCfg', 'FSusername')
        config_ini_info["fspassword"] = cfg.get('FileServerCfg', 'FSpassword')
        config_ini_info["fsdir"] = cfg.get('FileServerCfg', 'FSdir')

    # Get the user specify parameter from the command line
    parameter_info = utils.parse_parameter(args)
    parameter_info["image"] = args.image
    parameter_info["targets"] = args.targets
    parameter_info['fsprotocol'] = args.fsprotocol
    parameter_info['fsport'] = args.fsport
    parameter_info['fsip'] = args.fsip
    parameter_info['fsusername'] = args.fsusername
    parameter_info['fspassword'] = args.fspassword
    parameter_info['fsdir'] = args.fsdir

    # The parameters in the configuration file are used when the user does not specify parameters
    for key in parameter_info:
        if not parameter_info[key]:
            if key in config_ini_info:
                parameter_info[key] = config_ini_info[key]
    return parameter_info


if __name__ == '__main__':
    # Get parameters from config.ini and/or command line
    parameter_info = add_parameter()
    # Get connection info from the parameters user specified
    ip = parameter_info['ip']
    login_account = parameter_info["user"]
    login_password = parameter_info["passwd"]

    # Get set info from the parameters user specified
    try:
        image = parameter_info['image']
        targets = parameter_info['targets']
        fsprotocol = parameter_info['fsprotocol']
        fsport = parameter_info['fsport']
        fsip = parameter_info['fsip']
        fsusername = parameter_info['fsusername']
        fspassword = parameter_info['fspassword']
        fsdir = parameter_info['fsdir']
    except:
        sys.stderr.write("Please run the command 'python %s -h' to view the help info" % sys.argv[0])
        sys.exit(1)

    # Update firmware result and check result
    result = update_fw(ip, login_account, login_password, image, targets, fsprotocol, fsport, fsip, fsusername, fspassword, fsdir)
    if result['ret'] is True:
        del result['ret']
        sys.stdout.write(json.dumps(result['msg'], sort_keys=True, indent=2))
    else:
        sys.stderr.write(result['msg'])