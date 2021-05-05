import os
import logging
import sys
import glob
import telnetlib
import subprocess

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
  #check diagnosis mode - this is based off the environment variable DIAG_MODE
  # DIAG_MODE = GENERAL -> this does general checks on the container instance looking for errors in log files
  # DIAG_MODE = TASK    -> this checks the ECS agent logs for specific events relating to the TASK ID. TASK_ID must also be specified
  
  diag_mode = check_diag_mode()

  #check infra
  infra = check_infra()
  if infra == "AWS_ECS_EC2":
    a_logger.debug("This is running on EC2")
    if diag_mode == 'GENERAL':
      ec2_checks()
    elif diag_mode == 'TASK':
      task_id = os.environ['TASK_ID']
      a_logger.debug("Collecting events for task ID: "+task_id)
      #need to check its in all log files on the instance
      ecs_log_file = get_latest_file(ecs_logs_path+'/ecs/')
      get_task_events(task_id, ecs_log_file)
  else:
    a_logger.debug("This is running on Fargate")
    fargate_checks()
  #a_logger.debug("Directory contents for the config" + ecs_config_path+" path are: \n"+str(os.listdir(ecs_config_path)))
  
  #a_logger.debug("Directory contents for the logs" + ecs_logs_path+" path are: \n"+str(os.listdir(ecs_logs_path)))
  # list_ecs_log_files(ecs_logs_path+"/ecs")

  # #locate the latest ecs agent log
  # a_logger.debug("Finding latest log file:")
  # a_logger.debug(get_latest_file(ecs_logs_path+'/ecs/'))

  # connectivity_tests()

def get_task_events(task_id,ecs_log_file):
  log_line = ''
  with open(ecs_log_file) as openfile:
    for line in openfile:
      if task_id in line:
        log_line = log_line + line + "\n"

  with open("/tmp/task_events.log", "w") as writer:
    writer.write(log_line)

def check_diag_mode():
  diag_mode = os.environ['DIAG_MODE']
  return diag_mode

def ec2_checks():
  #check agent is running
  agent_running = agent_running_check()
  if agent_running:
    a_logger.debug("Agent is running")
  else:
    a_logger.debug("Agent is not running. ECS Agent logs need to be looked at.")
  

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
def connectivity_tests():
  a_logger.debug("Starting connectivity tests...")
  a_logger.debug("...")
  a_logger.debug("...")
  try:
    a_logger.debug("Testing https://"+ecs_endpoint)
    tn = telnetlib.Telnet(ecs_endpoint,port=443)
    a_logger.debug("Successfully connected to: https://"+ecs_endpoint)
  except Exception as error:
      a_logger.debug("Connection to endpoint"+ ecs_endpoint +" failed with: "+str(error))
  
  a_logger.debug("...")
  a_logger.debug("...")

def agent_running_check():
  with open("/tmp/output.log", "w") as output:
    a_logger.debug("Checking if agent is running with docker ps command...")
    subprocess.call("docker ps | grep amazon-ecs-agent", shell=True,stdout=output, stderr=output)

  agent_running = False
  with open("/tmp/output.log") as openfile:
    for line in openfile:
        if "amazon-ecs-agent" in line:
          agent_running = True
        else:
          agent_running = False
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
