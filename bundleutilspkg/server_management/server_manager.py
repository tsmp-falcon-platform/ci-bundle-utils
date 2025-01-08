import base64
from pathlib import Path
import shutil
import requests
import subprocess
import time
import os
import re
import sys
import logging
from packaging import version

import importlib.resources as pkg_resources

class JenkinsServerManager:

    def die(self, msg):
        logging.error(f"{msg}\n")
        sys.exit(1)

    def __init__(self, ci_type, ci_version, target_dir):
        """Initializes the Jenkins server manager with the specified ci_type, ci_version, and target directory."""
        if ci_type not in ['oc', 'oc-traditional', 'mm', 'cm']:
            self.die("Invalid type. Must be one of 'oc', 'oc-traditional', 'mm', or 'cm'")
        if not re.match(r'\d+\.\d+\.\d+\.\d+', ci_version):
            self.die("Invalid version. Must match the format 'W.X.Y.Z'")
        # user can specify a cache directory to store the downloaded WAR files by setting the environment variable BUNDLEUTILS_CACHE_DIR
        # defaults to the users home directory if not set
        if 'BUNDLEUTILS_CACHE_DIR' in os.environ:
            self.cache_dir = os.environ['BUNDLEUTILS_CACHE_DIR']
        else:
            self.cache_dir = os.path.join(os.path.expanduser("~"), ".bundleutils", "cache")
        self.war_cache_dir = os.path.join(self.cache_dir, "war", ci_type, ci_version)
        self.tar_cache_dir = os.path.join(self.cache_dir, "tar", ci_type, ci_version)
        self.tar_cache_file = os.path.join(self.tar_cache_dir, "jenkins.war")
        self.whoami_url = '/whoAmI/api/json?tree=authenticated'
        self.target_base_dir = '/tmp/ci_server_home'
        if not target_dir:
            target_dir = os.path.join(self.target_base_dir, ci_type, ci_version)
        self.ci_type = ci_type
        self.ci_version = ci_version
        self.target_dir = target_dir
        self.pid_file = os.path.join(target_dir, 'jenkins.pid')
        self.url_file = os.path.join(target_dir, 'jenkins.url')
        self.target_jenkins_home = os.path.join(target_dir, 'jenkins-home')
        self.target_jenkins_home_init_scripts = os.path.join(self.target_jenkins_home, 'init.groovy.d')
        self.target_jenkins_home_casc_startup_bundle = os.path.join(self.target_jenkins_home, 'casc-startup-bundle')
        self.target_jenkins_webroot = os.path.join(target_dir, 'jenkins-webroot')
        self.target_jenkins_log = os.path.join(target_dir, 'jenkins.log')
        self.war_path = os.path.join(self.target_jenkins_home, 'jenkins.war')
        self.war_cache_file = os.path.join(self.war_cache_dir, 'jenkins.war')
        self.war_cache_envelope_file = os.path.join(self.war_cache_dir, 'envelope.json')
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
            self.die(f"CI_TYPE '{self.ci_type}' not recognised", file=sys.stderr)

        return cb_docker_image, cb_war_download_url

    def copy_war_from_skopeo(self):
        if not os.path.exists(self.tar_cache_dir):
            os.makedirs(self.tar_cache_dir)
            # Copy image using skopeo
            subprocess.run(['skopeo', 'copy', f'docker://{self.cb_docker_image}', f'dir:{self.tar_cache_dir}'], check=True)
        else:
            logging.info(f"Found image in {self.tar_cache_dir}")

        if not os.path.exists(self.tar_cache_file):
            # Find and extract jenkins.war
            jenkins_war_found = False
            for f in sorted(Path(self.tar_cache_dir).glob('*'), key=os.path.getsize, reverse=True):
                try:
                    # run process in self.tar_cache_dir to avoid extracting the whole image
                    subprocess.run(['tar', '-C', self.tar_cache_dir, '--strip-components=3', '-xf', str(f), 'usr/share/jenkins/jenkins.war'], stderr=subprocess.DEVNULL, check=True)
                    logging.info(f"Found jenkins.war in {f}. Copying to war cache directory.")
                    shutil.copy(self.tar_cache_file, self.war_cache_file)
                    jenkins_war_found = True
                    break
                except subprocess.CalledProcessError:
                    continue
            # Check if jenkins.war was found
            if not jenkins_war_found:
                self.die("jenkins.war not found after extracting the Docker image.")

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
        logging.info(f"Copied WAR file to {self.war_cache_file}")

    def get_war(self):
        """Download the Jenkins WAR file for the specified type and version."""
        if not os.path.exists(self.war_cache_file):
            if not os.path.exists(self.war_cache_dir):
                os.makedirs(self.war_cache_dir)
            if self.cb_docker_image:
                # if docker on path or BUNDLEUTILS_USE_SKOPEO=1, use docker to copy the war file
                if shutil.which('docker') and os.getenv('BUNDLEUTILS_USE_SKOPEO') != '1':
                    self.copy_war_from_docker()
                elif shutil.which('skopeo'):
                    self.copy_war_from_skopeo()
                else:
                    self.die("Docker or Skopeo not found in path. No way of getting the WAR file from the docker image")
            elif self.cb_war_download_url:
                self.download_war()
            else:
                self.die("No download URL or Docker image specified")
        else:
            logging.debug(f"WAR file already exists at {self.war_cache_file}")
        # recreate the jenkins-home directory
        logging.info(f"Recreating {self.target_jenkins_home}")
        if os.path.exists(self.target_jenkins_home):
            subprocess.run(['rm', '-r', self.target_jenkins_home], check=True)
        os.makedirs(self.target_jenkins_home)
        # copy the WAR file to the target directory
        logging.info(f"Copying WAR file to {self.war_path}")
        subprocess.run(['cp', self.war_cache_file, self.war_path], check=True)

    def download_war(self):
        """Download the Jenkins WAR file for the specified type and version."""
        response = requests.get(self.cb_war_download_url)
        if response.status_code == 200:
            with open(self.war_cache_file, 'wb') as file:
                file.write(response.content)
            logging.info(f"Downloaded WAR version {self.ci_version} to {self.war_cache_file}")
        else:
            self.die(f"Failed to download WAR file from {self.cb_war_download_url}. Status code: {response.status_code}")

    def test_java_specification_version(self, version):
        try:
            # Run the `java` command to print the `java.specification.version` property
            result = subprocess.run(
                ['java', '-XshowSettings:properties', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # The properties usually come in stderr, not stdout
            output = result.stderr

            # Look for the `java.specification.version` property in the output
            for line in output.splitlines():
                if "java.specification.version" in line:
                    version_str = line.split('=')[1].strip()

                    # The `java.specification.version` is already the major version
                    return version_str == version

            # If version information wasn't found, return None or raise an error
            self.die("Java version could not be found. Check the output of 'java -XshowSettings:properties -version'")

        except FileNotFoundError:
            self.die("Java is not installed or not found in PATH.")

    def create_startup_bundle(self, plugin_files, validation_template):
        """Create a startup bundle from the specified source directory and bundle template."""
        if not plugin_files:
            self.die(f"Plugin files not found in {plugin_files}")
        # the validation template is a directory containing the configuration files to be used
        if not validation_template or os.path.exists(validation_template):
            # check if the validation-template directory exists in the current directory
            if os.path.exists('validation-template'):
                logging.info('Using validation-template in the current directory')
                validation_template = 'validation-template'
            else:
                # check if the validation-template directory exists in the defaults.configs package
                logging.info('Using validation-template from the defaults.configs package')
                validation_template = pkg_resources.files('defaults.configs') / 'validation-template'
        logging.info(f"Using validation template '{validation_template}'")
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
        logging.info(f"Created startup bundle in {self.target_jenkins_home_casc_startup_bundle}")

    def start_server(self):
        """Start the Jenkins server using the downloaded WAR file."""
        if not os.path.exists(self.war_path):
            logging.info("WAR file does not exist. Getting now...")
            self.get_war()

        # if the ci_version is lower than 2.440.1.3, check for a JAVA_HOME_11 variable, and set it
        # https://docs.cloudbees.com/docs/release-notes/latest/cloudbees-ci/modern-cloud-platforms/2.440.1.3
        required_java_version = '17'
        if version.parse(self.ci_version) < version.parse('2.440.1.3'):
            required_java_version = '11'
            if 'JAVA_HOME_11' in os.environ:
                logging.info(f"Setting JAVA_HOME to {os.environ['JAVA_HOME_11']}")
                self.jvm_cache_dir = os.environ['JAVA_HOME_11']
                os.environ['JAVA_HOME'] = self.jvm_cache_dir
                os.environ['PATH'] = f"{os.environ['JAVA_HOME']}/bin:{os.environ['PATH']}"
            else:
                logging.info("Java 11 required but JAVA_HOME_11 not set. Defaulting to JAVA_HOME...") 

        # check for JAVA_HOME and use it if set
        if 'JAVA_HOME' in os.environ:
            logging.info(f"JAVA_HOME is set to {os.environ['JAVA_HOME']}")
            java = os.path.join(os.environ['JAVA_HOME'], 'bin', 'java')
            if not os.path.exists(java):
                self.die(f"JAVA_HOME is set to {os.environ['JAVA_HOME']} but {java} does not exist.")

        self.test_java_specification_version(required_java_version)
        # print the java -version output
        subprocess.run([java, '-version'], check=True)

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
        if os.environ.get("CASC_VALIDATION_LICENSE_KEY_B64"):
            logging.info("Decoding the license key and cert...")
            casc_validation_license_key_b64 = os.environ["CASC_VALIDATION_LICENSE_KEY_B64"]
            casc_validation_license_cert_b64 = os.environ.get("CASC_VALIDATION_LICENSE_CERT_B64", "")
            os.environ["CASC_VALIDATION_LICENSE_KEY"] = base64.b64decode(casc_validation_license_key_b64).decode('utf-8')
            os.environ["CASC_VALIDATION_LICENSE_CERT"] = base64.b64decode(casc_validation_license_cert_b64).decode('utf-8')

        # Fail if either CASC_VALIDATION_LICENSE_KEY or CASC_VALIDATION_LICENSE_CERT are not set
        if not os.environ.get("CASC_VALIDATION_LICENSE_KEY") and not os.environ.get("IGNORE_LICENSE"):
            self.die("CASC_VALIDATION_LICENSE_KEY is not set.")
        if not os.environ.get("CASC_VALIDATION_LICENSE_CERT") and not os.environ.get("IGNORE_LICENSE"):
            self.die("CASC_VALIDATION_LICENSE_CERT is not set.")

        # if CASC_VALIDATION_LICENSE_KEY contains a literal newline, replace it with a newline character
        os.environ["CASC_VALIDATION_LICENSE_KEY"] = os.getenv('CASC_VALIDATION_LICENSE_KEY','').replace("\\n", "\n")
        os.environ["CASC_VALIDATION_LICENSE_CERT"] = os.getenv('CASC_VALIDATION_LICENSE_CERT','').replace("\\n", "\n")

        # Add token script to init.groovy.d
        with open(os.path.join(self.target_jenkins_home_init_scripts, "init_02_admin_token.groovy"), "w") as file:
            file.write(token_script)

        java_opts = os.getenv('BUNDLEUTILS_CI_JAVA_OPTS', '')
        http_port = os.getenv('BUNDLEUTILS_HTTP_PORT', '8080')
        # if port is already in use, fail
        try:
            response = requests.get(f"http://localhost:{http_port}{self.whoami_url}")
            if response.status_code == 200:
                self.die(f"Port {http_port} is already in use. Please specify a different port using the BUNDLEUTILS_HTTP_PORT environment variable.")
        except requests.ConnectionError:
            pass
        # write the server URL to the jenkins_url file
        with open(self.url_file, 'w') as file:
            file.write(f"http://localhost:{http_port}")
        jenkins_opts = os.getenv('BUNDLEUTILS_JENKINS_OPTS', '')
        # if BUNDLEUTILS_JENKINS_OPTS contains -Dcore.casc.config.bundle, fail
        if "core.casc.config.bundle" in jenkins_opts or "core.casc.config.bundle" in java_opts:
            self.die("BUNDLEUTILS_JENKINS_OPTS or BUNDLEUTILS_CI_JAVA_OPTS contains core.casc.config.bundle. This is not allowed.")
        # if self.target_jenkins_home_casc_startup_bundle doesn't exist, fail
        if not os.path.exists(self.target_jenkins_home_casc_startup_bundle):
            self.die(f"Startup bundle {self.target_jenkins_home_casc_startup_bundle} does not exist.")
        # if java_opts not empty, add ' -Dcore.casc.config.bundle=/tmp/validation-bundle', else set it
        if java_opts:
            java_opts += f" -Dcore.casc.config.bundle={self.target_jenkins_home_casc_startup_bundle}"
        else:
            java_opts = f"-Dcore.casc.config.bundle={self.target_jenkins_home_casc_startup_bundle}"
        # create the command to start the Jenkins server by joining the elements in the list
        command = [java]
        command.extend(java_opts.split())
        command.extend(['-jar', self.war_path, f"--httpPort={http_port}", f"--webroot={self.target_jenkins_webroot}"])
        command.extend(jenkins_opts.split())
        command = [element.strip() for element in command if element and element.strip()]
        env = os.environ.copy()
        env['JENKINS_HOME'] = self.target_jenkins_home
        # if ADMIN_PASSWORD env var not set, create a random password
        if 'ADMIN_PASSWORD' not in os.environ:
            logging.info("ADMIN_PASSWORD not set. Creating a random password...")
            admin_password = os.urandom(16).hex()
            env['ADMIN_PASSWORD'] = admin_password
            logging.info(f"Temporary ADMIN_PASSWORD set to: {admin_password}")
        logging.info(f"Starting Jenkins server with command: {' '.join(command)}")
        with open(self.target_jenkins_log, 'w') as log_file:
            process = subprocess.Popen(command, env=env, stdout=log_file, stderr=subprocess.STDOUT)
        with open(self.pid_file, 'w') as file:
            file.write(str(process.pid))
        logging.info(f"Jenkins server starting with PID {process.pid}")
        logging.info(f"Jenkins server logging to {self.target_jenkins_log}")
        self.wait_for_server()
        self.check_auth_token()
        # look for any WARN or ERROR messages in the log, and print the log line if found
        logging.info("Jenkins server - Checking for WARN or ERROR messages in the Jenkins log...")
        with open(self.target_jenkins_log, 'r', encoding='utf-8') as log_file:
            for line in log_file:
                if 'WARN' in line or 'ERROR' in line:
                    logging.warn(line)
        logging.info("Jenkins server - Finished checking the Jenkins log")

    def get_envelope_json_from_war(self):
        if os.path.exists(self.war_cache_envelope_file):
            logging.info(f"Reading envelope.json from {self.war_cache_envelope_file}")
            with open(self.war_cache_envelope_file, 'r') as file:
                envelope_json = file.read()
            return envelope_json
        # read the envelope.json from self. /WEB-INF/plugins/envelope.json
        self.get_war()
        # extract the /WEB-INF/plugins/envelope.json from the WAR file
        with subprocess.Popen(['unzip', '-p', self.war_path, 'WEB-INF/plugins/envelope.json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            envelope_json, _ = process.communicate()
            envelope_json = envelope_json.decode('utf-8')
        if not envelope_json:
            self.die(f"WEB-INF/plugins/envelope.json not found in {self.war_cache_file}")
        with open(self.war_cache_envelope_file, 'wb') as file:
            file.write(envelope_json.encode('utf-8'))
        return envelope_json

    def get_envelope_json(self):
        # read the envelope.json from self.target_jenkins_webroot /WEB-INF/plugins/envelope.json
        envelope_json = os.path.join(self.target_jenkins_webroot, 'WEB-INF', 'plugins', 'envelope.json')
        if not os.path.exists(envelope_json):
            self.die(f"envelope.json not found in {envelope_json}")
        with open(envelope_json, 'r') as file:
            # read as json
            envelope_json = file.read()
        return envelope_json

    def get_server_url(self):
        # Get the Jenkins server url, username, and password (from self.target_jenkins_home/secrets/initialAdminToken)
        with open(self.url_file, 'r') as file:
            server_url = file.read().strip()
        return server_url

    def get_server_details(self):
        # Get the Jenkins server url, username, and password (from self.target_jenkins_home/secrets/initialAdminToken)
        with open(os.path.join(self.target_jenkins_home, 'secrets', 'initialAdminToken'), 'r') as file:
            initial_admin_token = file.read().strip()
        server_url = self.get_server_url()
        return server_url, 'admin', initial_admin_token

    def check_auth_token(self):
        logging.info("Checking authentication token...")
        headers = {}
        server_url, username, password = self.get_server_details()
        url = f"{server_url}{self.whoami_url}"
        if username and password:
            headers['Authorization'] = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
        # zip and post the YAML to the URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # ensure the response is valid JSON and the authorities key contains a list with at least one element called authenticated
        response_json = response.json()
        if 'authenticated' not in response_json:
            logging.error(f"Response: {response_json}")
            self.die("ERROR: Authentication failed. Please check the username and password.")
        else:
            # print the response
            logging.info(f"Authentication successful. Response: {response_json}")

    def wait_for_server(self):
        """Wait for the Jenkins server to start."""
        server_started = False
        CONNECT_MAX_WAIT = 60
        end_time = time.time() + CONNECT_MAX_WAIT
        logging.info("Waiting for server to start...")
        server_url = self.get_server_url()
        while time.time() < end_time:
            try:
                response = requests.get(f"{server_url}{self.whoami_url}")
                if response.status_code == 200:
                    server_started = True
                    time.sleep(5)
                    logging.info("Server started")
                    break
                else:
                    time.sleep(5)
                    logging.info("Waiting for server to start...")
            except requests.ConnectionError:
                time.sleep(5)
                logging.info("Waiting for server to start...")
        if not server_started:
            logging.warn("ERROR: Server not started in time. Printing the Jenkins log....")
            with open(self.target_jenkins_log, "r", encoding='utf-8') as log_file:
                logging.info(log_file.read())
            self.stop_server()
            self.die("ERROR: Server not started in time. Please check the Jenkins log for more information.")

    def stop_server(self):
        """Stop the Jenkins server using the PID file."""
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as file:
                pidstr = file.read().strip()
                os.remove(self.pid_file)
                if os.path.exists(self.url_file):
                    os.remove(self.url_file)
                if not pidstr:
                    logging.info("PID file is empty.")
                else:
                    # check if the PID is a valid integer
                    if not pidstr.isdigit():
                        logging.info("PID file does not contain a valid PID.")
                    else:
                        logging.info(f"Stopping server with PID {pidstr}")
                        pid = int(pidstr)
                        try:
                            os.kill(pid, 15)  # SIGTERM
                            logging.info(f"Stopped Jenkins server with PID {pid}")
                        except ProcessLookupError:
                            logging.info("Process not found. It may have already been stopped.")
        else:
            logging.info("PID file not found. Is the server running?")
            # glob for files matching "target_base_dir/.*/.*/jenkins.pid"
            pid_files = Path(self.target_base_dir).glob('**/jenkins.pid')
            for pid_file in pid_files:
                logging.info(f"Perhaps this one -> {pid_file}")

