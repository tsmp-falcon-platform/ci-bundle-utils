#! /bin/bash

./00-verify.sh
./01-createBundleUtilSecrets.sh
./02-applyCronJob.sh
./03-readJobLogs.sh