# ECS AutoDiag
This project was designed to enable troubleshooting on the ECS infrastructure. The tool runs certain diagnostic tests and collects information based on the set environment variables. Below are the details of how to make use of the tool. The `Examples` section can also be looked at to narrow down the specific use case needed for use with the tool.

## Supported Infrastructure
- ECS Fargate
- ECS EC2 Launch Type

# How to use AutoDiag [EC2 launch type]
`!!! NOTE: The mounts are only needed if using the EC2 launch type.`
1. When using the EC2 launch type, the task definition needs to have the mount points and volumes specified as can be seen in the `ec2-taskdefinition.json`:

```
...
...
"mountPoints": [
          {
            "containerPath": "/var/run/docker.sock",
            "sourceVolume": "docker"
          },
          {
            "containerPath": "/var/log",
            "sourceVolume": "logs"
          },
          {
            "containerPath": "/etc/config",
            "sourceVolume": "config"
          }
        ]
...
...
"volumes": [
      {
        "name": "docker",
        "host": {
          "sourcePath": "/var/run/docker.sock"
        }
      },
      {
        "name": "logs",
        "host": {
          "sourcePath": "/var/log"
        }
      },
      {
        "name": "config",
        "host": {
          "sourcePath": "/etc/ecs"
        }
      }
    ]
```
Details of these mounts and why they are needed can be found below:
| Container Path | Host Path | Description | 
| ------------- | ------------- | ------------- |
| /var/run/docker.sock | /var/run/docker.sock | This will allow for autodiag to check if the agent container is running. |
| /var/log | /var/log | This allows autodiag to access the logs on the instance. |
| /etc/ecs | /etc/ecs | This allows autodiag to access the ECS agent configuration. |

2. You can then create the task definition by running the following command:

``` 
$ aws ecs register-task-definition --cli-input-json file://ec2-taskdefinition.json
```
Use the `fargate-taskdefinition.json` if running AutoDiag on Fargate.

3. Ensure that the task execution role or container instance role that the task runs on has the permissions to access cloudwatch logs i.e. `logs:CreateLogStream` and `logs:PutLogEvents`. The ECS agent also needs to be configured to support the `awslogs` log driver. If using Fargate, ensure that the task execution role has the cloudwatch permissions. 

All the logs the diagnosis events will be streamed to the cloudwatch log stream for the task. 

## Example Use Cases

### [EC2 Launch Type] I dont have SSH access to my container instances and I need to collect logs [DIAG_MODE = GENERAL]
In this case, you might need to be able to get logs from an instance but SSH access to the instance is disabled. ECS Autodiag will run on the instance by mounting the /var/log and /etc/ecs host directories onto the container and performing some standard service endpoint connectivity tests. Autdiag will then filter the ECS agent logs for any failures or errors and output the full log line for the given error/failure. 

```
$ aws ecs start-task \
    --cluster <cluster-name> \
    --task-definition autodiag:1 \
    --overrides '{ "containerOverrides": [ { "name": "autodiag", "environment": [ { "name": "DIAG_MODE", "value": "GENERAL" } ] } ] }' \
    --container-instances <container-instance-id> 
```
Note: the task definition family can be retrieved from the output of `Step 2`. 

If the `task definition` is being used as is in `taskdefinition.json`, then the task definition family will be set as `autodiag`. If this is the first task definition family named `autodiag`, the version will be set to `1`.

Also, replace the container instance ID with the container instance where you want autodiag to run. 

AutoDiag will generate the output of its diagnosis in the cloudwatch log stream for the task.

### [EC2 & Fargate] Tasks are failing health checks [DIAG_MODE = HEALTH_CHECK]
In this case, you might need to be able to confirm the response coming from your task health check endpoint. Be sure to launch the autodiag task in one of the subnets used by the load balancer and have the task use the same security group used by the load balancer. Note that the task security group needs to allow the autodiag task on the health check port. 

Environment variables used in this case:

| Environment Variable Key | Environment Variable Value | Description | Required environmental variables | 
| ------------- | ------------- | ------------- | ------------- |
| DIAG_MODE | `HEALTHCHECK` | Sends a request against the specified IP and path and returns the response code. The ENDPOINT, PORT and PROTOCOL environment variables must also be set. | `PROTOCOL`, `PORT`, `ENDPOINT` |
| ENDPOINT | `<endpoint1>` | The endpoint that the connectivity tests will be done on. | `HEALTHCHECK` or `CONNECTIVITY`|
| PORT | `<port>` | The port that will be connected to. This works with the ENDPOINT environment variable. | `ENDPOINT` |


#### EC2 Launch Type
```
$ aws ecs start-task \
    --cluster <cluster-name> \
    --task-definition autodiag:1 \
    --overrides '{ "containerOverrides": [ { "name": "autodiag", "environment": [ { "name": "DIAG_MODE", "value": "HEALTHCHECK" }, { "name": "ENDPOINT", "value": "10.0.5.10/healthcheck"}, { "name": "PORT", "value": "80" }, { "name": "PROTOCOL", "value": "http" } ] } ] }' \
    --container-instances <container-instance-id> 
```
In the above, change the `ENDPOINT` to the `taskIP/healthcheckPath`, the `PORT` to the healthcheck port and the `PROTOCOL` to the healthcheck protocol. 

We use the StartTask API call here to be able to control exactly which container instance we want the autodiag task to run on. When on Fargate, we will use the RunTask API call to start the autodiag task.

#### Fargate Launch Type
```
$ aws ecs run-task \
    --cluster <cluster-name> \
    --task-definition autodiag:1 \
    --launch-type "FARGATE" \
    --overrides '{ "containerOverrides": [ { "name": "autodiag", "environment": [ { "name": "DIAG_MODE", "value": "HEALTHCHECK" }, { "name": "ENDPOINT", "value": "`10.0.5.10/healthcheck`"}, { "name": "PORT", "value": "`80`" }, { "name": "PROTOCOL", "value": "`http`" } ] } ] }' \
    --network-configuration "awsvpcConfiguration={subnets=[`subnet-abcd1234`],securityGroups=[`sg-abcd1234`],assignPublicIp=`<ENABLED/DISABLED>`}"
```
In the above, please ensure to change the values of `ENDPOINT`, `PORT` and `PROTOCOL`. In addition, ensure that the network configuration has the correct values specified for the `subnets`, `securityGroups` and `assignPublicIp`.

### Tasks cant connect to database/endpoint

### Task is stuck in a pending state.

### Tasks unable to resolve endpoint


## Environment Variables
| Environment Variable Key | Environment Variable Value | Description | Required environmental variables | 
| ------------- | ------------- | ------------- | ------------- |
| DIAG_MODE  | `GENERAL` | This does general checks on the container instance looking for errors in log files | N/A |
| DIAG_MODE | `TASK` | This checks the ECS agent logs for specific events relating to the TASK ID. TASK_ID must also be specified. | `TASK_ID`|
| TASK_ID | `<task_id>` | The task ID that is being looked at. Seeing as the TASK diagnsis mode does not check the validity of the task ID, any substring can be used in place of the `task_id` and Autodiag will filter the logs for the substring specified. | N/A |
| DIAG_MODE | CONNECTIVITY | This checks endpoint and DNS tests for the specified endpoint in the ENDPOINT and PORT environment variables. | `ENDPOINT`, `PORT` |
| ENDPOINT | `<endpoint1>` | The endpoint that the connectivity tests will be done on. | `HEALTHCHECK` or `CONNECTIVITY`|
| PORT | `<port>` | The port that will be connected to. This works with the ENDPOINT environment variable. | `ENDPOINT` |
| DIAG_MODE | `HEALTHCHECK` | Sends a request against the specified IP and path and returns the response code. The ENDPOINT, PORT and PROTOCOL environment variables must also be set. | `PROTOCOL`, `PORT`, `ENDPOINT` |
| PROTOCOL | `http`,`https` | The protocol used for the health check. | `HEALTHCHECK`, `PORT`|
| DIAG_MODE | `MYSQL_CONNECTION` | Connects to the specified MYSQL database. This environment variable requires the database connection environment variables USER, PASSWORD, HOST and DATABASE. Note that DB credentials should not be passed in plain text. Rather use secrets or parameter store as specified in the [ECS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html) | `USER`, `PASSWORD`, `HOST`, `DATABASE` |
| USER | `<user>` | The database user. | `HOST`, `PASSWORD`, `DATABASE`, `MYSQL_CONNECTION` |
| PASSWORD | `<password>` | The database password. | `HOST`, `DATABASE`, `USER`, `MYSQL_CONNECTION` |
| HOST | `<host>` | The database host. | `DATABASE`, `PASSWORD`, `USER`, `MYSQL_CONNECTION` |
| DATABASE | `<database>` | The database name. | `HOST`, `PASSWORD`, `USER`, `MYSQL_CONNECTION` |
| S3_LOGS_ENDPOINT | `<endpoint>` | The S3 logs uploader endpoint that the script should push the zip file to. This is shared by AWS Support. This feature is still being worked on. | N/A |

