###
#
# Lenovo Redfish examples - Clear System log
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
import lenovo_utils as utils


def clear_system_log(ip, login_account, login_password, system_id):
    """Clear system log    
    :params ip: BMC IP address
    :type ip: string
    :params login_account: BMC user name
    :type login_account: string
    :params login_password: BMC user password
    :type login_password: string
    :params system_id: ComputerSystem instance id(None: first instance, All: all instances)
    :type system_id: None or string
    :returns: returns clear system log result when succeeded or error message when failed
    """
    result = {}
    login_host = 'https://' + ip
    try:
        # Connect using the BMC address, account name, and password
        # Create a REDFISH object
        REDFISH_OBJ = redfish.redfish_client(base_url=login_host, username=login_account,
                                             password=login_password, default_prefix='/redfish/v1')
        # Login into the server and create a session
        REDFISH_OBJ.login(auth="session")
    except:
        result = {'ret': False, 'msg': "Please check the username, password, IP is correct"}
        return result
    try:
        # Get response_base_url resource
        response_base_url = REDFISH_OBJ.get('/redfish/v1', None)
        if response_base_url.status == 200:
            managers_url = response_base_url.dict['Managers']['@odata.id']
        else:
            error_message = utils.get_extended_error(response_base_url)
            result = {'ret': False, 'msg': "Url '/redfish/v1' response Error code %s \nerror_message: %s" % (response_base_url.status, error_message)}
            return result

        # Get managers url resource
        response_managers_url = REDFISH_OBJ.get(managers_url, None)
        if response_managers_url.status == 200:
            manager_count = response_managers_url.dict['Members@odata.count']
        else:
            error_message = utils.get_extended_error(response_managers_url)
            result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (managers_url,response_managers_url.status, error_message)}
            return result
        for i in range(manager_count):
            manager_x_url = response_managers_url.dict['Members'][i]['@odata.id']
            response_manager_x_url = REDFISH_OBJ.get(manager_x_url, None)
            if response_manager_x_url.status == 200:
                # Get the log server url
                log_services_url = response_manager_x_url.dict['LogServices']['@odata.id']
            else:
                error_message = utils.get_extended_error(response_manager_x_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (manager_x_url, response_manager_x_url.status, error_message)}
                return result

            # Get the response log server resource
            response_log_services_url = REDFISH_OBJ.get(log_services_url, None)
            if response_log_services_url.status == 200:
                members = response_log_services_url.dict['Members']
            else:
                error_message = utils.get_extended_error(response_log_services_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (log_services_url, response_log_services_url.status,error_message)}
                return result
            for member in members:
                log_url = member['@odata.id']
                response_log_url = REDFISH_OBJ.get(log_url, None)
                if "Actions" in response_log_url.dict:
                    if "#LogService.ClearLog" in response_log_url.dict["Actions"]:
                        # Get the clear system log url
                        clear_log_url = response_log_url.dict["Actions"]["#LogService.ClearLog"]["target"]
                        headers = {"Content-Type":"application/json"}

                        # Build request body and send requests to clear the system log
                        body = {"Action": "LogService.ClearLog"}
                        response_clear_log = REDFISH_OBJ.post(clear_log_url, headers=headers, body=body)
                        if response_clear_log.status in [200, 204]:
                            result = {'ret': True, 'msg': "Clear log successfully"}
                        else:
                            error_message = utils.get_extended_error(response_clear_log)
                            result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (clear_log_url, response_clear_log.status, error_message)}
    except Exception as e:
        result = {'ret': False, 'msg': "error_message: %s" % (e)}
    finally:
        REDFISH_OBJ.logout()
        return result


if __name__ == '__main__':
    # Get parameters from config.ini and/or command line
    argget = utils.create_common_parameter_list()
    args = argget.parse_args()
    parameter_info = utils.parse_parameter(args)
    
    # Get connection info from the parameters user specified
    ip = parameter_info['ip']
    login_account = parameter_info["user"]
    login_password = parameter_info["passwd"]
    system_id = parameter_info['sysid']
    
    # Get clear system log result and check result
    result = clear_system_log(ip, login_account, login_password, system_id)
    if result['ret'] is True:
        del result['ret']
        sys.stdout.write(json.dumps(result['msg'], sort_keys=True, indent=2))
    else:
        sys.stderr.write(result['msg'])