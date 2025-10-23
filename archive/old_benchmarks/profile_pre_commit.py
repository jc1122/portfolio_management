import subprocess
import time

import yaml

with open(".pre-commit-config.yaml") as f:
    config = yaml.safe_load(f)

with open("pre-commit-profile.log", "w") as log_file:
    for repo in config["repos"]:
        for hook in repo["hooks"]:
            hook_id = hook["id"]
            log_file.write(f"Running hook: {hook_id}\n")
            start_time = time.time()
            process = subprocess.run(
                ["pre-commit", "run", hook_id, "--all-files"],
                check=False,
                capture_output=True,
                text=True,
            )
            end_time = time.time()
            duration = end_time - start_time
            log_file.write(f"Duration: {duration:.2f}s\n")
            log_file.write(f"Stdout:\n{process.stdout}\n")
            log_file.write(f"Stderr:\n{process.stderr}\n")
            log_file.write("-" * 20 + "\n")
