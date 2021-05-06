# ECS Auto Diag
This project was designed to enable troubleshooting on the ECS infrastructure. The tool runs certain diagnostic tests and collects information based on the set environment variables. Below are the details of how to make use of the tool. The `Examples` section can also be looked at to narrow down the specific use case needed for use with the tool.

## Supported Infrastructure
- ECS Fargate
- ECS EC2 Launch Type

## Task Definition
The task definition needs to specify the environment variables and mounts. The environment variables are desribed in the `Environment variables` section. The mounts need to be specified as follows:

- 

## Environment variables
| Environment Variable Key | Environment Variable Value | Description | 
| ------------- | ------------- | ------------- |
| DIAG_MODE  | GENERAL | This does general checks on the container instance looking for errors in log files |
| DIAG_MODE | TASK | This checks the ECS agent logs for specific events relating to the TASK ID. TASK_ID must also be specified. |
| TASK_ID | `task_id` | The task ID that is being looked at. |
| DIAG_MODE | CONNECTIVITY | This checks endpoint and DNS tests for the specified endpoint in the ENDPOINT and PORT environment variables. |
| ENDPOINT | ['`endpoint1`', '`endpoint2`'] | A list of endpoints that the connectivity tests will be done on. |
| S3_LOGS_ENDPOINT | `endpoint` | The S3 logs uploader endpoint that the script should push the zip file to. This is shared by AWS Support. |
