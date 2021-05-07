# ECS AutoDiag
This project was designed to enable troubleshooting on the ECS infrastructure. The tool runs certain diagnostic tests and collects information based on the set environment variables. Below are the details of how to make use of the tool. The `Examples` section can also be looked at to narrow down the specific use case needed for use with the tool.

## Supported Infrastructure
- ECS Fargate
- ECS EC2 Launch Type

## Example Use Cases

### I dont have SSH access to my container instances and I need to collect logs

### Tasks are failing health checks

### Tasks cant connect to database/endpoint

### Task is stuck in a pending state.

### Tasks unable to resolve endpoint


## Environment Variables
| Environment Variable Key | Environment Variable Value | Description | Required environmental variables | 
| ------------- | ------------- | ------------- | ------------- |
| DIAG_MODE  | `GENERAL` | This does general checks on the container instance looking for errors in log files | N/A |
| DIAG_MODE | `TASK` | This checks the ECS agent logs for specific events relating to the TASK ID. TASK_ID must also be specified. | `TASK_ID`|
| TASK_ID | `<task_id>` | The task ID that is being looked at. Seeing as the TASK diagnsis mode does not check the validity of the task ID, any substring can be used in place of the `task_id` and Autodiag will filter the logs for the substring specified. |
| DIAG_MODE | CONNECTIVITY | This checks endpoint and DNS tests for the specified endpoint in the ENDPOINT and PORT environment variables. | `ENDPOINT`, `PORT` |
| ENDPOINT | `<endpoint1>` | The endpoint that the connectivity tests will be done on. | `HEALTHCHECK` or `CONNECTIVITY`|
| PORT | `<port>` | The port that will be connected to. This works with the ENDPOINT environment variable. | `ENDPOINT` |
| DIAG_MODE | `HEALTHCHECK` | Sends a request against the specified IP and path and returns the response code. The ENDPOINT, PORT and PROTOCOL environment variables must also be set. | `PROTOCOL`, `PORT` |
| PROTOCOL | `http`,`https` | The protocol used for the health check. | `HEALTHCHECK`, `PORT`|
| DIAG_MODE | `MYSQL_CONNECTION` | Connects to the specified MYSQL database. This environment variable requires the database connection environment variables USER, PASSWORD, HOST and DATABASE. Note that DB credentials should not be passed in plain text. Rather use secrets or parameter store as specified in the [ECS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html) | `USER`, `PASSWORD`, `HOST`, `DATABASE` |
| USER | `<user>` | The database user. | `HOST`, `PASSWORD`, `DATABASE`, `MYSQL_CONNECTION` |
| PASSWORD | `<password>` | The database password. | `HOST`, `DATABASE`, `USER`, `MYSQL_CONNECTION` |
| HOST | `<host>` | The database host. | `DATABASE`, `PASSWORD`, `USER`, `MYSQL_CONNECTION` |
| DATABASE | `<database>` | The database name. | `HOST`, `PASSWORD`, `USER`, `MYSQL_CONNECTION` |
| S3_LOGS_ENDPOINT | `<endpoint>` | The S3 logs uploader endpoint that the script should push the zip file to. This is shared by AWS Support. | N/A |

## Task Definition
The task definition needs to specify the environment variables and mounts. The environment variables are described in the `Environment variables` section. The bind mounts need to be specified as follows:
`!!! NOTE: The mounts are only needed if using the EC2 launch type.`
```
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
        ],
```
With the associated volumes:
```
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