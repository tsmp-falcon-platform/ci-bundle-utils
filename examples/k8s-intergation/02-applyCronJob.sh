#! /bin/bash

set -euo pipefail

NAMESPACE="${1:-cbci}"
YAML_FILE="yaml/bu-audit-k8s-crontask.yaml"
CRONJOB_NAME="bundleutils-audit"

echo "🔄 Reapplying CronJob '$CRONJOB_NAME' from $YAML_FILE..."
kubectl config set-context --current --namespace=$NAMESPACE
kubectl delete -f "$YAML_FILE" --ignore-not-found
kubectl apply -f "$YAML_FILE"

echo "⏳ Waiting for job to be scheduled..."
echo "🔍 Wait some seconds, until the first job is started, the run ./03-readJobLogs.sh"
#sleep 130
#echo "🔍 Finding the most recent job created by the CronJob..."
#kubectl logs -f $(kubectl get pods --selector=job-name=$(kubectl get jobs --sort-by=.metadata.creationTimestamp | grep $CRONJOB_NAME  | head -n 1 | awk '{print $1}') -o jsonpath='{.items[0].metadata.name}')
