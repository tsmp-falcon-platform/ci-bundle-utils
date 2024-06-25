import base64
import requests
import subprocess
import time
import os
import re
import sys
import importlib.resources as pkg_resources

class JenkinsServerManager:
    def __init__(self, ci_type, ci_version, target_dir):
        """Initializes the Jenkins server manager with the specified ci_type, ci_version, and target directory."""
        if ci_type not in ['oc', 'oc-traditional', 'mm', 'cm']:
            sys.exit("Invalid type. Must be one of 'oc', 'oc-traditional', 'mm', or 'cm'")
        if not re.match(r'\d+\.\d+\.\d+\.\d+', ci_version):
            sys.exit("Invalid version. Must match the format 'W.X.Y.Z'")
        # user can specify a cache directory to store the downloaded WAR files by setting the environment variable BUNDLEUTILS_CACHE_DIR
        # defaults to the users home directory if not set
        if 'BUNDLEUTILS_CACHE_DIR' in os.environ:
            self.war_cache_dir = os.environ['BUNDLEUTILS_CACHE_DIR']
        else:
            self.war_cache_dir = os.path.join(os.path.expanduser("~"), ".bundleutils", "cache", "war", ci_type, ci_version)
        if not target_dir:
            target_dir = os.path.join('/tmp/ci_server_home', ci_type, ci_version)
        self.ci_type = ci_type
        self.ci_version = ci_version
        self.target_dir = target_dir
        self.pid_file = os.path.join(target_dir, 'jenkins.pid')
        self.target_jenkins_home = os.path.join(target_dir, 'jenkins-home')
        self.target_jenkins_home_init_scripts = os.path.join(self.target_jenkins_home, 'init.groovy.d')
        self.target_jenkins_home_casc_startup_bundle = os.path.join(self.target_jenkins_home, 'casc-startup-bundle')
        self.target_jenkins_webroot = os.path.join(target_dir, 'jenkins-webroot')
        self.target_jenkins_log = os.path.join(target_dir, 'jenkins.log')
        self.war_path = os.path.join(self.target_jenkins_home, 'jenkins.war')
        self.war_cache_file = os.path.join(self.war_cache_dir, 'jenkins.war')
        self.cb_docker_image, self.cb_war_download_url = self.set_cloudbees_variables()
        if not os.path.exists(self.target_jenkins_home_init_scripts):
            os.makedirs(self.target_jenkins_home_init_scripts)
        if not os.path.exists(self.target_jenkins_home_init_scripts):
            os.makedirs(self.target_jenkins_home_init_scripts)
        if not os.path.exists(self.target_jenkins_webroot):
            os.makedirs(self.target_jenkins_webroot)

    def set_cloudbees_variables(self):
        cb_downloads_url = "https://downloads.cloudbees.com/cloudbees-core/traditional"
        cb_docker_image = None
        cb_war_download_url = None

        if self.ci_type == "mm":
            cb_docker_image = f"cloudbees/cloudbees-core-mm:{self.ci_version}"
        elif self.ci_type == "oc":
            cb_docker_image = f"cloudbees/cloudbees-cloud-core-oc:{self.ci_version}"
        elif self.ci_type == "cm":
            cb_war_download_url = f"{cb_downloads_url}/client-master/rolling/war/{self.ci_version}/cloudbees-core-cm.war"
        elif self.ci_type == "oc-traditional":
            cb_war_download_url = f"{cb_downloads_url}/operations-center/rolling/war/{self.ci_version}/cloudbees-core-oc.war"
        else:
            sys.exit(f"CI_TYPE '{self.ci_type}' not recognised", file=sys.stderr)

        return cb_docker_image, cb_war_download_url

    def copy_war_from_docker(self):
        """Copy the Jenkins WAR file from the Docker container to the target directory."""
        # Pull the Docker image
        subprocess.run(['docker', 'pull', f'{self.cb_docker_image}'], check=True)

        # Create a container without starting it
        container_id = subprocess.check_output(['docker', 'create', f'{self.cb_docker_image}']).decode().strip()

        # Copy the Jenkins WAR file from the created container
        subprocess.run(['docker', 'cp', f'{container_id}:/usr/share/jenkins/jenkins.war', self.war_cache_file], check=True)

        # Remove the created container
        subprocess.run(['docker', 'rm', container_id], check=True)
        print(f"Copied WAR file to {self.war_cache_file}")

    def get_war(self):
        """Download the Jenkins WAR file for the specified type and version."""
        if not os.path.exists(self.war_cache_file):
            if not os.path.exists(self.war_cache_dir):
                os.makedirs(self.war_cache_dir)
            if self.cb_docker_image:
                self.copy_war_from_docker()
            elif self.cb_war_download_url:
                self.download_war()
            else:
                sys.exit("No download URL or Docker image specified")
        else:
            print(f"WAR file already exists at {self.war_cache_file}")
        # recreate the jenkins-home directory
        print(f"Recreating {self.target_jenkins_home}")
        if os.path.exists(self.target_jenkins_home):
            subprocess.run(['rm', '-r', self.target_jenkins_home], check=True)
        os.makedirs(self.target_jenkins_home)
        # copy the WAR file to the target directory
        print(f"Copying WAR file to {self.war_path}")
        subprocess.run(['cp', self.war_cache_file, self.war_path], check=True)

    def download_war(self):
        """Download the Jenkins WAR file for the specified type and version."""
        response = requests.get(self.cb_war_download_url)
        if response.status_code == 200:
            with open(self.war_cache_file, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded WAR version {self.ci_version} to {self.war_cache_file}")
        else:
            sys.exit(f"Failed to download WAR file from {self.cb_war_download_url}. Status code: {response.status_code}")

    def create_startup_bundle(self, plugin_files, validation_template):
        """Create a startup bundle from the specified source directory and bundle template."""
        if not plugin_files:
            sys.exit(f"Plugin files not found in {plugin_files}")
        # the validation template is a directory containing the configuration files to be used
        if not validation_template or os.path.exists(validation_template):
            # check if the validation-template directory exists in the current directory
            if os.path.exists('validation-template'):
                print('Using validation-template in the current directory')
                validation_template = 'validation-template'
            else:
                # check if the validation-template directory exists in the defaults.configs package
                print('Using validation-template from the defaults.configs package')
                validation_template = pkg_resources.files('defaults.configs') / 'validation-template'
        else:
            print(f"Using validation template '{validation_template}'")
        # recreate the  target_jenkins_home_casc_startup_bundle directory
        if os.path.exists(self.target_jenkins_home_casc_startup_bundle):
            subprocess.run(['rm', '-r', self.target_jenkins_home_casc_startup_bundle], check=True)
        os.makedirs(self.target_jenkins_home_casc_startup_bundle)
        # copy the files in the validation template directory to the target_jenkins_home_casc_startup_bundle directory
        for root, dirs, files in os.walk(validation_template):
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(self.target_jenkins_home_casc_startup_bundle, os.path.relpath(src_file, validation_template))
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                subprocess.run(['cp', src_file, dest_file], check=True)
        for plugin_file in plugin_files:
            subprocess.run(['cp', plugin_file, self.target_jenkins_home_casc_startup_bundle], check=True)
        print(f"Created startup bundle in {self.target_jenkins_home_casc_startup_bundle}")

    def start_server(self):
        """Start the Jenkins server using the downloaded WAR file."""
        if not os.path.exists(self.war_path):
            print("WAR file does not exist. Getting now...")
            self.get_war()

        token_script="""
        import hudson.model.User
        import jenkins.security.ApiTokenProperty
        def jenkinsTokenName = 'token-for-test'
        def user = User.get('admin', false)
        def apiTokenProperty = user.getProperty(ApiTokenProperty.class)
        apiTokenProperty.tokenStore.getTokenListSortedByName().findAll {it.name==jenkinsTokenName}.each {
            apiTokenProperty.tokenStore.revokeToken(it.getUuid())
        }
        def result = apiTokenProperty.tokenStore.generateNewToken(jenkinsTokenName).plainValue
        user.save()
        new File(System.getenv('JENKINS_HOME') + "/secrets/initialAdminToken").text = result
        """
        # Account for the case where the license is base64 encoded
        if "CASC_VALIDATION_LICENSE_KEY_B64" in os.environ:
            print("Decoding the license key and cert...")
            casc_validation_license_key_b64 = os.environ["CASC_VALIDATION_LICENSE_KEY_B64"]
            casc_validation_license_cert_b64 = os.environ.get("CASC_VALIDATION_LICENSE_CERT_B64", "")
            os.environ["CASC_VALIDATION_LICENSE_KEY"] = base64.b64decode(casc_validation_license_key_b64).decode('utf-8')
            os.environ["CASC_VALIDATION_LICENSE_CERT"] = base64.b64decode(casc_validation_license_cert_b64).decode('utf-8')

        # Fail if either CASC_VALIDATION_LICENSE_KEY or CASC_VALIDATION_LICENSE_CERT are not set
        if not os.environ.get("CASC_VALIDATION_LICENSE_KEY") and not os.environ.get("IGNORE_LICENCE"):
            sys.exit("CASC_VALIDATION_LICENSE_KEY is not set.")
        if not os.environ.get("CASC_VALIDATION_LICENSE_CERT") and not os.environ.get("IGNORE_LICENCE"):
            sys.exit("CASC_VALIDATION_LICENSE_CERT is not set.")

        # Add token script to init.groovy.d
        with open(os.path.join(self.target_jenkins_home_init_scripts, "init_02_admin_token.groovy"), "w") as file:
            file.write(token_script)

        java_opts = os.getenv('BUNDLE_UTILS_JAVA_OPTS', '')
        http_port = os.getenv('BUNDLE_UTILS_HTTP_PORT', '8080')
        # if port is already in use, fail
        try:
            response = requests.get(f"http://localhost:{http_port}/whoAmI/api/json")
            if response.status_code == 200:
                sys.exit(f"Port {http_port} is already in use. Please specify a different port using the BUNDLE_UTILS_HTTP_PORT environment variable.")
        except requests.ConnectionError:
            pass
        self.server_url = f"http://localhost:{http_port}"
        jenkins_opts = os.getenv('BUNDLE_UTILS_JENKINS_OPTS', '')
        # if BUNDLE_UTILS_JENKINS_OPTS contains -Dcore.casc.config.bundle, fail
        if "core.casc.config.bundle" in jenkins_opts or "core.casc.config.bundle" in java_opts:
            sys.exit("BUNDLE_UTILS_JENKINS_OPTS or BUNDLE_UTILS_JAVA_OPTS contains core.casc.config.bundle. This is not allowed.")
        # if self.target_jenkins_home_casc_startup_bundle doesn't exist, fail
        if not os.path.exists(self.target_jenkins_home_casc_startup_bundle):
            sys.exit(f"Startup bundle {self.target_jenkins_home_casc_startup_bundle} does not exist.")
        # add -Dcore.casc.config.bundle=/tmp/validation-bundle to the jenkins_opts
        java_opts += f" -Dcore.casc.config.bundle={self.target_jenkins_home_casc_startup_bundle}"
        command = ['java', java_opts, '-jar', self.war_path, f"--httpPort={http_port}", f"--webroot={self.target_jenkins_webroot}", jenkins_opts]
        # command = ['java', '-jar', self.war_path, f"--httpPort={http_port}", f"--webroot={self.target_jenkins_webroot}"]
        command = [element.strip() for element in command if element and element.strip()]
        env = os.environ.copy()
        env['JENKINS_HOME'] = self.target_jenkins_home
        # if ADMIN_PASSWORD env var not set, create a random password
        if 'ADMIN_PASSWORD' not in os.environ:
            print("ADMIN_PASSWORD not set. Creating a random password...")
            admin_password = os.urandom(16).hex()
            env['ADMIN_PASSWORD'] = admin_password
            print(f"Temporary ADMIN_PASSWORD set to: {admin_password}")
        print(f"Starting Jenkins server with command: {' '.join(command)}")
        with open(self.target_jenkins_log, 'w') as log_file:
            process = subprocess.Popen(command, env=env, stdout=log_file, stderr=subprocess.STDOUT)
        with open(self.pid_file, 'w') as file:
            file.write(str(process.pid))
        print(f"Jenkins server starting with PID {process.pid}")
        print(f"Jenkins server logging to {self.target_jenkins_log}")
        self.wait_for_server()

    def wait_for_server(self):
        """Wait for the Jenkins server to start."""
        server_started = False
        CONNECT_MAX_WAIT = 60
        end_time = time.time() + CONNECT_MAX_WAIT
        print("Waiting for server to start...")
        while time.time() < end_time:
            try:
                response = requests.get(f"{self.server_url}/whoAmI/api/json")
                if response.status_code == 200:
                    server_started = True
                    time.sleep(5)
                    print("Server started")
                    break
                else:
                    time.sleep(5)
                    print("Waiting for server to start...")
            except requests.ConnectionError:
                time.sleep(5)
                print("Waiting for server to start...")
        if not server_started:
            print("ERROR: Server not started in time. Printing the Jenkins log....")
            with open(self.target_jenkins_log, "r") as log_file:
                print(log_file.read())
            self.stop_server()
            sys.exit(1)

    def stop_server(self):
        """Stop the Jenkins server using the PID file."""
        try:
            with open(self.pid_file, 'r') as file:
                pid = int(file.read().strip())
            os.kill(pid, 15)  # SIGTERM
            print(f"Stopped Jenkins server with PID {pid}")
        except FileNotFoundError:
            print("PID file not found. Is the server running?")
        except ProcessLookupError:
            print("Process not found. It may have already been stopped.")
