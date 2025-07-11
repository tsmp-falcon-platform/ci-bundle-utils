# Kubernetes SSH Secret


## Pre-Requirements

* SSH config for GitHub
* id_rsa (GitHub SSH private key)
* known_hosts



## Setup 

See 
    * https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent
    * https://docs.github.com/en/authentication/connecting-to-github-with-ssh
    * https://stackoverflow.com/questions/3225862/multiple-github-accounts-ssh-config


* config
```
Host github.com
User <YOUR_GITHUB_USER>
Hostname ssh.github.com
AddKeysToAgent yes
PreferredAuthentications publickey
IdentitiesOnly yes
IdentityFile /root/.ssh/id_rsa
Port 443
```

* known_hosts
```
ssh-keyscan -H github.com >> known_hosts
```

Once you have all 3 files in one directory:

```
kubectl create secret generic secret-ssh-auth --type=kubernetes.io/ssh-auth   --from-file=./
```
