import os
import logging
import sys
import glob
import telnetlib
import subprocess
import requests
import json

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
  ##########################################################################################
  # Supported environment variables
  ##########################################################################################
  # DIAG_MODE = GENERAL      -> this does general checks on the container instance looking for errors in log files
  # DIAG_MODE = TASK         -> this checks the ECS agent logs for specific events relating to the TASK ID. TASK_ID must also be specified.
  # TASK_ID   = <task_id>    -> the task ID that is being looked at.
  # DIAG_MODE = CONNECTIVITY -> this checks endpoint and DNS tests for the specified endpoint in the ENDPOINT and PORT environment variables.
  # ENDPOINT = <endpoint>    -> the endpoint that will be connected to.
  # LOGS_S3_ENDPOINT         -> the S3 logs uploader endpoint that the script should push the zip file to.
  ##########################################################################################

  diag_mode = check_diag_mode()
  if diag_mode:
    #check infra
    infra = check_infra()
    if infra == "AWS_ECS_EC2":
      a_logger.debug("## This is running on EC2 ##")
      a_logger.debug(" ")
      if diag_mode == 'GENERAL':
        ec2_checks()
        endpoints = get_ecs_endpoints(get_region())
        for endpoint in endpoints:
          connectivity_tests(endpoint, 443)
        #check_logs()
      elif diag_mode == 'TASK':
        task_id = os.environ['TASK_ID']
        a_logger.debug("Collecting events for task ID: "+task_id)
        #need to check its in all log files on the instance
        ecs_log_file = get_latest_file(ecs_logs_path+'/ecs/')
        get_task_events(task_id, ecs_log_file)
    else:
      a_logger.debug("## This is running on Fargate")
      a_logger.debug(" ")
      fargate_checks()

# assuming task metadata v4
def get_region():
  #task_metadata_endpoint = str(os.environ["ECS_CONTAINER_METADATA_URI_V4"])+"/task"
  #task_metadata = json.loads(requests.get(task_metadata_endpoint))
  return 'us-east-1'

def get_ecs_endpoints(region):
  ecs_endpoints = [
    'ecs.'+region+'.amazonaws.com',
    'ecs-fips.'+region+'.amazonaws.com'
  ]
  return ecs_endpoints

def get_task_events(task_id,ecs_log_file):
  log_line = ''
  with open(ecs_log_file) as openfile:
    for line in openfile:
      if task_id in line:
        log_line = log_line + line + "\n"

  with open("/tmp/task_events.log", "w") as writer:
    writer.write(log_line)

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

#connectivity tests
def connectivity_tests(endpoint,port):
  a_logger.debug("## Starting connectivity tests... ##")
  a_logger.debug("...")
  a_logger.debug("...")
  try:
    a_logger.debug("-> Testing https://"+endpoint)
    tn = telnetlib.Telnet(ecs_endpoint,port=port)
    a_logger.debug("  -> Successfully connected to: https://"+endpoint)
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

def get_latest_file(path):
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