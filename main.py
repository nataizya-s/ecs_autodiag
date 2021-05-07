import os
import logging
import sys
import glob
import telnetlib
import subprocess
import requests
import json
import socket
import time

a_logger = logging.getLogger()
a_logger.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
a_logger.addHandler(stdout_handler)

#get region from environment variables/task metadata endpoint
region = 'us-east-1'
ecs_endpoint = 'ecs.'+region+'.amazonaws.com'

#directories
ecs_config_path = '/etc/ecs'
ecs_logs_path = '/var/log'

def start():

  # add health check diag mode and ability to filter logs for a particular word
  # add mysql connection test with credentials
  diag_mode = check_diag_mode()
  if diag_mode:

    #check infra
    infra = check_infra()
    if infra == "AWS_ECS_EC2":
      
      a_logger.debug("## This is running on EC2 ##")

      if diag_mode == 'GENERAL':
        env_vars = ''
        a_logger.debug("## The environment variables set in the diag container are: ")
        for var in os.environ:
            env_vars = env_vars + var + "\n"
        a_logger.debug(env_vars)

        a_logger.debug("## DIAG_MODE = GENERAL. Performing GENERAL dignosis checks.")

        ec2_checks()
        
        endpoints = get_ecs_endpoints(get_region())

        #check connectivity to ECS service endpoints.
        for endpoint in endpoints:
          connectivity_tests(endpoint, 443)

        check_logs()
      
      elif diag_mode == 'TASK':
        a_logger.debug("## DIAG_MODE = TASK_ID. Performing task specific dignosis checks.")

        task_id = os.environ['TASK_ID']

        a_logger.debug("Collecting events for task ID: "+task_id)

        #need to check its in all log files on the instance
        ecs_log_file = get_latest_ecs_agent_log_file(ecs_logs_path+'/ecs/')
        a_logger.debug(ecs_log_file)
        log_files = get_all_ecs_log_files(ecs_logs_path+'/ecs/')
        a_logger.debug("## Checking events for task in the latest log file...")
        a_logger.debug(get_events(task_id,ecs_log_file))
        a_logger.debug("## Checking events for task in the other agent log files...")

        a_logger.debug("The agent log files on the instance are "+str(log_files))
        if log_files:
          for log_file in log_files:
            a_logger.debug(get_events(task_id, log_file))
        else:
          a_logger.debug("No log files exist on the instance.")
      
      elif diag_mode == 'CONNECTIVITY':
        endpoint = os.environ['ENDPOINT']
        if 'PORT' in os.environ:
          port = os.environ['PORT']
          connectivity_tests(endpoint, port)
        else:
          a_logger.debug("There is no port specified. Please specify a port to test connectivity with.")
        
      #Current supported traffic is HTTP
      elif diag_mode == 'HEALTHCHECK':
        a_logger.debug("## DIAG_MODE = HEALTHCHECK. Performing 3 health checks with 10 seconds between each one.")
        if 'ENDPOINT' in os.environ and 'PROTOCOL' in os.environ and 'PORT' in os.environ:
          endpoint = os.environ['ENDPOINT']
          protocol = os.environ['PROTOCOL']
          port = os.environ['PORT']
          healthchecks(endpoint, protocol,port)
        elif 'ENDPOINT' not in os.environ:
          a_logger.debug("Please specify the ENDPOINT environment variable.")
        elif 'PROTOCOL' not in os.environ:
          a_logger.debug("Please specify the PROTOCOL environment variable.")
        elif 'PORT' not in os.environ:
          a_logger.debug("Please specify the PORT environment variable.")

    else:
      a_logger.debug("## This is running on Fargate")
      #fargate_checks()
    
    a_logger.debug("#### DIAG COMPLETE ####")

def healthchecks(endpoint, protocol, port):
  dns_resol = dns_check(endpoint)
  if dns_resol:
    if protocol == 'http' or protocol == 'https':
      try:
        endpoint = protocol+'://'+endpoint+":"+str(port)
        for hc in range(1,4):
          response_code = requests.get(endpoint).status_code
          a_logger.debug("Health check ["+str(hc)+"]: Status Code "+str(response_code))
          time.sleep(10)
      except Exception as e:
         a_logger.debug("Failed to run healthcheck request. "+ str(e))
  else:
    a_logger.debug("DNS resolution for "+endpoint+" failed.")

def get_all_ecs_log_files(path):
  ecs_agent_log_files = []  
  if os.path.exists(path):
    list_of_files = os.listdir(path)
    full_path = [path+"{0}".format(x) for x in list_of_files]
    
    for file in full_path:
      if 'ecs-agent' in file:
        ecs_agent_log_files.append(file)
    return ecs_agent_log_files
  else:
    latest_agent_log = "Path does not exist."
    return ecs_agent_log_files

def check_logs():
  a_logger.debug('## Checking the latest ECS agent logs.')
  try:
    latest_agent_log = get_latest_ecs_agent_log_file(ecs_logs_path+'/ecs/')
    # Filter for any errors
    errors = ['Error', 'error', 'Failed', 'failed', 'Timeout', 'timeout', 'Refused', 'refused']
    log_events = ''
    for error in errors:
      log_events = log_events + get_events(error,latest_agent_log)
    if log_events == '':
      message = "There are no errors in the ECS agent logs..."
      a_logger.debug("## The following errors are in the ECS agent logs: "+latest_agent_log+" \n"+message)
    else:
      a_logger.debug("## The following errors are in the ECS agent logs: \n"+log_events)

    a_logger.debug("## End of ECS log events ##")
  except Exception as e:
    a_logger.debug("Unable to get the latest ECS agent log file or filter the agent logs "+ str(e))

def get_region():
  #currently not supporting version 2
  try:
    #metadata version 4
    if "ECS_CONTAINER_METADATA_URI_V4" in os.environ:
      env_variable = "ECS_CONTAINER_METADATA_URI_V4"
    
    #metadata version 3
    elif "ECS_CONTAINER_METADATA_URI" in os.environ:
      env_variable = "ECS_CONTAINER_METADATA_URI"

    task_metadata_endpoint = str(os.environ[env_variable])+"/task"

  except Exception as e:
    a_logger.debug("Error in getting metadata URI: "+str(e))

  try:
    task_metadata = requests.get(task_metadata_endpoint).json()
  except Exception as e:
    a_logger.debug("Error accessing metadata: "+str(e))

  task_arn = task_metadata['TaskARN']
  region = task_arn.split(':')[3]
  return region

def get_ecs_endpoints(region):
  ecs_endpoints = [
    'ecs.'+region+'.amazonaws.com',
    'ecs-fips.'+region+'.amazonaws.com'
  ]
  return ecs_endpoints

def get_events(substring,ecs_log_file):
  log_line = ''
  with open(ecs_log_file) as openfile:
    for line in openfile:
      if substring in line:
        log_line = log_line + line + "\n"

  with open("/tmp/"+substring+"_events.log", "w") as writer:
    writer.write(log_line)
  
  return log_line

def check_diag_mode():
  try:
    diag_mode = os.environ["DIAG_MODE"]
    #diag_mode = os.environ.get("DIAG_MODE")
    return diag_mode
  except Exception as e:
    a_logger.debug("DIAD_MODE has not been set. Ensure the DIAG_MODE environment variable is set.")
    return False

"""
TODO: iptables for task roles - based off log collector, the following:
       - iptables -nvL -t filter
       - iptables -nvL -t nat 
    - possibly leverage the existing log collector.
- this only checks the agent status using the docker run command.
"""
def ec2_checks():
  #check agent is running
  agent_running = agent_running_check()
  if agent_running:
    a_logger.debug("-> ECS Agent is running :)")
  else:
    a_logger.debug("-> ECS Agent is not running :(")
    a_logger.debug("   ** ECS Agent logs need to be looked at **")
  
def check_infra():
  env = os.environ['AWS_EXECUTION_ENV']
  return env

def list_ecs_log_files(path):
  a_logger.debug("Directory contents for the logs"+ ecs_logs_path+" path are: \n")
  files = os.listdir(path)
  file_str = ''
  for file in files:
    file_str = file_str + file +"\n"
  a_logger.debug(file_str)

def dns_check(endpoint):
  dns_resol = False
  try:
    addr = socket.gethostbyname(endpoint)
    a_logger.debug("Endpoint resolves to: "+addr)
    dns_resol = True
  except Exception as error:
      a_logger.debug("-> DNS resolution of endpoint"+endpoint+" failed with: "+str(error))
  
  return dns_resol
#connectivity tests
def connectivity_tests(endpoint,port):
  a_logger.debug("## Starting connectivity tests... ##")
  a_logger.debug("-> Checking DNS resolution...")
  
  dns_resol = dns_check(endpoint)

  if dns_resol:
    try:
      a_logger.debug("-> Testing "+endpoint)
      tn = telnetlib.Telnet(ecs_endpoint,port=port)
      a_logger.debug("  -> Successfully connected to: "+endpoint)
    except Exception as error:
        a_logger.debug("-> Connection to endpoint"+endpoint+" failed with: "+str(error))
  
#check if agent is running
def agent_running_check():
  try:
    agent_running = False

    with open("/tmp/output.log", "w") as output:
      a_logger.debug("Checking if agent is running with docker ps command...")
      subprocess.call("docker ps | grep amazon-ecs-agent", shell=True,stdout=output, stderr=output)

    with open("/tmp/output.log") as openfile:
      for line in openfile:
          if "amazon-ecs-agent" in line:
            agent_running = True
          else:
            agent_running = False

  except Exception as e:
    a_logger.debug("Unable to check if ECS agent container is running: "+str(e))
    return agent_running

  
  return agent_running

#log file checks

#check if task ID env variable is set to narrow down log file filtering 

def get_latest_ecs_agent_log_file(path):
  if os.path.exists(path):
    list_of_files = os.listdir(path)
    full_path = [path+"{0}".format(x) for x in list_of_files]
    ecs_agent_log_files = []  
    for file in full_path:
      if 'ecs-agent' in file:
        ecs_agent_log_files.append(file)
    latest_agent_log = max(ecs_agent_log_files, key=os.path.getctime)
  else:
    latest_agent_log = "Path does not exist."
    return latest_agent_log
  return latest_agent_log

start()
